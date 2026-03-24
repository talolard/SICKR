"""SQLAlchemy-backed catalog retrieval and hydration repository."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy import Engine, Row, and_, bindparam, case, delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from ikea_agent.chat.product_images import build_catalog_image_url
from ikea_agent.retrieval.catalog_models import ProductImageRecord
from ikea_agent.retrieval.schema import (
    product_embedding_neighbors,
    product_embeddings,
    products_canonical,
)
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult

_MIN_PAIRWISE_KEY_COUNT = 2
_DEFAULT_COUNTRY = "Germany"
_QUERY_VECTOR_BINDPARAM = bindparam(
    "query_vector",
    type_=product_embeddings.c.embedding_vector.type,
)
_READ_EMBEDDING_ROWS_QUERY = (
    select(
        product_embeddings.c.canonical_product_key,
        product_embeddings.c.embedding_model,
        product_embeddings.c.embedding_vector,
    )
    .where(product_embeddings.c.embedding_model == bindparam("embedding_model"))
    .order_by(product_embeddings.c.canonical_product_key)
)
_READ_EMBEDDINGS_FOR_SIMILARITY_QUERY = select(
    product_embeddings.c.canonical_product_key,
    product_embeddings.c.embedding_vector,
).where(
    product_embeddings.c.embedding_model == bindparam("embedding_model"),
    product_embeddings.c.canonical_product_key.in_(bindparam("product_keys", expanding=True)),
)
_READ_PRODUCT_BY_KEY_QUERY = (
    select(
        products_canonical.c.canonical_product_key,
        products_canonical.c.product_name,
        products_canonical.c.product_type,
        products_canonical.c.description_text,
        product_embeddings.c.embedded_text,
        products_canonical.c.main_category,
        products_canonical.c.sub_category,
        products_canonical.c.dimensions_text,
        products_canonical.c.width_cm,
        products_canonical.c.depth_cm,
        products_canonical.c.height_cm,
        products_canonical.c.price_eur,
        products_canonical.c.url,
        products_canonical.c.display_title,
    )
    .select_from(
        products_canonical.outerjoin(
            product_embeddings,
            (
                product_embeddings.c.canonical_product_key
                == products_canonical.c.canonical_product_key
            ),
        )
    )
    .where(
        products_canonical.c.country == _DEFAULT_COUNTRY,
        products_canonical.c.canonical_product_key == bindparam("canonical_product_key"),
    )
    .limit(1)
)
_NEIGHBOR_SIMILARITIES_QUERY = select(
    product_embedding_neighbors.c.source_product_key,
    product_embedding_neighbors.c.neighbor_product_key,
    product_embedding_neighbors.c.cosine_similarity,
).where(
    product_embedding_neighbors.c.embedding_model == bindparam("embedding_model"),
    product_embedding_neighbors.c.source_product_key.in_(bindparam("source_keys", expanding=True)),
    product_embedding_neighbors.c.neighbor_product_key.in_(
        bindparam("neighbor_keys", expanding=True)
    ),
)


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """One ranked semantic match used by the legacy non-Postgres fallback path."""

    canonical_product_key: str
    semantic_score: float


class CatalogRepository:
    """Run semantic catalog retrieval and map rows to typed results."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def search_semantic_products(
        self,
        *,
        query_vector: tuple[float, ...],
        embedding_model: str,
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        """Return hydrated search results for one semantic query."""

        if not query_vector or result_limit <= 0:
            return []
        if self._engine.dialect.name != "postgresql":
            return self._search_semantic_products_legacy(
                query_vector=query_vector,
                embedding_model=embedding_model,
                filters=filters,
                result_limit=result_limit,
            )

        statement = _build_postgres_search_statement(filters)
        with self._engine.connect() as connection:
            rows = connection.execute(
                statement,
                {
                    **_filter_params(filters),
                    "embedding_model": embedding_model,
                    "query_vector": list(query_vector),
                    "result_limit": result_limit,
                },
            ).fetchall()
        return [_search_row_to_result(row) for row in rows]

    def hydrate_candidates(
        self,
        *,
        candidates: Sequence[VectorMatch],
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        """Apply filters and hydrate vector hits with typed catalog rows."""

        if not candidates:
            return []
        candidate_scores = {
            item.canonical_product_key: item.semantic_score
            for item in candidates
            if item.canonical_product_key
        }
        candidate_ranks = {
            item.canonical_product_key: rank
            for rank, item in enumerate(candidates, start=1)
            if item.canonical_product_key
        }
        if not candidate_scores:
            return []

        with self._engine.connect() as connection:
            rows = cast(
                "list[Row[tuple[object, ...]]]",
                connection.execute(
                    _build_legacy_hydration_statement(filters),
                    {
                        **_filter_params(filters),
                        "candidate_keys": list(candidate_scores),
                    },
                ).fetchall(),
            )
        hydrated_results: list[RetrievalResult] = []
        for row in rows:
            canonical_product_key = str(row[0])
            semantic_score = candidate_scores.get(canonical_product_key)
            if semantic_score is None:
                continue
            hydrated_results.append(
                _legacy_row_to_result(
                    row,
                    semantic_score=semantic_score,
                )
            )
        hydrated_results.sort(
            key=lambda item: _legacy_result_sort_key(
                result=item,
                sort_mode=filters.sort,
                candidate_rank=candidate_ranks.get(item.canonical_product_key, result_limit + 1),
            )
        )
        return hydrated_results[:result_limit]

    def read_neighbor_similarities(
        self,
        *,
        embedding_model: str,
        product_keys: Sequence[str],
    ) -> dict[tuple[str, str], float]:
        """Read pairwise cosine similarities for a candidate key set."""

        normalized_keys = [key for key in dict.fromkeys(product_keys) if key]
        if len(normalized_keys) < _MIN_PAIRWISE_KEY_COUNT:
            return {}
        if self._engine.dialect.name == "postgresql":
            return self._read_neighbor_similarities_postgres(
                embedding_model=embedding_model,
                product_keys=normalized_keys,
            )
        return self._read_neighbor_similarities_legacy(
            embedding_model=embedding_model,
            product_keys=normalized_keys,
        )

    def _read_neighbor_similarities_postgres(
        self,
        *,
        embedding_model: str,
        product_keys: Sequence[str],
    ) -> dict[tuple[str, str], float]:
        """Compute candidate-set pair similarities directly in Postgres."""

        with self._engine.connect() as connection:
            rows = cast(
                "list[tuple[object, ...]]",
                connection.execute(
                    _build_postgres_neighbor_similarity_statement(),
                    {
                        "embedding_model": embedding_model,
                        "source_keys": product_keys,
                        "neighbor_keys": product_keys,
                    },
                ).fetchall(),
            )
        lookup: dict[tuple[str, str], float] = {}
        for row in rows:
            source_key = _str_or_none(row[0])
            neighbor_key = _str_or_none(row[1])
            similarity = _float_or_none(row[2])
            if source_key is None or neighbor_key is None or similarity is None:
                continue
            lookup[(source_key, neighbor_key)] = similarity
        return lookup

    def read_image_urls_by_product_keys(
        self,
        *,
        canonical_product_keys: Sequence[str],
        serving_strategy: Literal["backend_proxy", "direct_public_url"],
        base_url: str | None,
    ) -> dict[str, tuple[str, ...]]:
        """Return ordered image URLs for each requested canonical product key."""

        normalized_keys = [key for key in dict.fromkeys(canonical_product_keys) if key]
        if not normalized_keys:
            return {}
        with Session(self._engine) as session:
            records = session.scalars(
                select(ProductImageRecord)
                .where(ProductImageRecord.canonical_product_key.in_(normalized_keys))
                .order_by(
                    ProductImageRecord.canonical_product_key.asc(),
                    _image_order_priority(ProductImageRecord.is_og_image),
                    ProductImageRecord.image_rank.asc().nulls_last(),
                    ProductImageRecord.image_asset_key.asc(),
                )
            ).all()
        image_urls: dict[str, list[str]] = {}
        counts_by_key: dict[str, int] = {}
        for record in records:
            key = record.canonical_product_key
            counts_by_key[key] = counts_by_key.get(key, 0) + 1
            image_urls.setdefault(key, []).append(
                build_catalog_image_url(
                    product_id=record.product_id,
                    ordinal=counts_by_key[key],
                    public_url=record.public_url,
                    serving_strategy=serving_strategy,
                    base_url=base_url,
                    image_asset_key=record.image_asset_key,
                    crawl_run_id=record.crawl_run_id,
                )
            )
        return {key: tuple(urls) for key, urls in image_urls.items()}

    def resolve_product_image_path(
        self,
        *,
        product_id: str,
        ordinal: int | None = None,
    ) -> Path | None:
        """Return one local image path for a product id and optional ordinal."""

        if not product_id:
            return None
        target_ordinal = 1 if ordinal is None else ordinal
        if target_ordinal < 1:
            return None
        with Session(self._engine) as session:
            records = session.scalars(
                select(ProductImageRecord)
                .where(
                    ProductImageRecord.product_id == product_id,
                    ProductImageRecord.local_path.is_not(None),
                )
                .order_by(
                    _image_order_priority(ProductImageRecord.is_og_image),
                    ProductImageRecord.image_rank.asc().nulls_last(),
                    ProductImageRecord.image_asset_key.asc(),
                )
                .limit(target_ordinal)
            ).all()
        if len(records) < target_ordinal:
            return None
        local_path = records[target_ordinal - 1].local_path
        if local_path is None:
            return None
        candidate = Path(local_path).expanduser()
        if not candidate.exists():
            return None
        return candidate.resolve()

    def _read_neighbor_similarities_legacy(
        self,
        *,
        embedding_model: str,
        product_keys: Sequence[str],
    ) -> dict[tuple[str, str], float]:
        """Support non-Postgres test engines until the old compatibility layer is deleted."""

        with self._engine.connect() as connection:
            rows = cast(
                "list[tuple[object, ...]]",
                connection.execute(
                    _NEIGHBOR_SIMILARITIES_QUERY,
                    {
                        "embedding_model": embedding_model,
                        "source_keys": product_keys,
                        "neighbor_keys": product_keys,
                    },
                ).fetchall(),
            )
        lookup: dict[tuple[str, str], float] = {}
        for row in rows:
            source_key = _str_or_none(row[0])
            neighbor_key = _str_or_none(row[1])
            similarity = _float_or_none(row[2])
            if source_key is None or neighbor_key is None or similarity is None:
                continue
            lookup[(source_key, neighbor_key)] = similarity
        computed_lookup = _compute_neighbor_similarities_from_embeddings(
            engine=self._engine,
            embedding_model=embedding_model,
            product_keys=product_keys,
        )
        for key_pair, similarity in computed_lookup.items():
            lookup.setdefault(key_pair, similarity)
        return lookup

    def read_product_by_key(self, *, product_key: str) -> RetrievalResult | None:
        """Return one typed product row by canonical product key."""

        if not product_key:
            return None
        with self._engine.connect() as connection:
            row = connection.execute(
                _READ_PRODUCT_BY_KEY_QUERY,
                {"canonical_product_key": product_key},
            ).fetchone()
        if row is None:
            return None
        return RetrievalResult(
            canonical_product_key=str(row[0]),
            product_name=str(row[1]),
            product_type=_str_or_none(row[2]),
            description_text=_str_or_none(row[3]),
            embedding_text=_format_embedding_text(row[4]),
            main_category=_str_or_none(row[5]),
            sub_category=_str_or_none(row[6]),
            dimensions_text=_str_or_none(row[7]),
            width_cm=_float_or_none(row[8]),
            depth_cm=_float_or_none(row[9]),
            height_cm=_float_or_none(row[10]),
            price_eur=_float_or_none(row[11]),
            url=_str_or_none(row[12]),
            semantic_score=0.0,
            filter_pass_reasons=("product_lookup",),
            rank_explanation="product lookup by canonical key",
            display_title=_str_or_none(row[13]),
        )

    def _search_semantic_products_legacy(
        self,
        *,
        query_vector: tuple[float, ...],
        embedding_model: str,
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        """Fallback for non-Postgres test engines."""

        candidates = _rank_embedding_rows(
            rows=EmbeddingSnapshotRepository(self._engine).read_embedding_rows(embedding_model),
            query_vector=query_vector,
            result_limit=result_limit,
        )
        return self.hydrate_candidates(
            candidates=candidates,
            filters=filters,
            result_limit=result_limit,
        )


class EmbeddingSnapshotRepository:
    """Load embedding snapshot rows for snapshot-build and legacy compatibility tooling."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def read_embedding_rows(self, embedding_model: str) -> list[tuple[str, str, tuple[float, ...]]]:
        """Read embedding rows from seeded catalog snapshot tables."""

        with self._engine.connect() as connection:
            rows = connection.execute(
                _READ_EMBEDDING_ROWS_QUERY,
                {"embedding_model": embedding_model},
            ).fetchall()
        return [
            (str(row[0]), str(row[1]), _vector_from_value(row[2]))
            for row in rows
            if row[2] is not None
        ]

    def replace_neighbor_rows(
        self,
        *,
        embedding_model: str,
        rows: Sequence[tuple[str, str, int, float]],
    ) -> int:
        """Replace precomputed neighbor rows for one embedding model in one batch."""

        with self._engine.begin() as connection:
            connection.execute(
                delete(product_embedding_neighbors).where(
                    product_embedding_neighbors.c.embedding_model == embedding_model
                )
            )
            if not rows:
                return 0
            connection.execute(
                product_embedding_neighbors.insert(),
                [
                    {
                        "embedding_model": embedding_model,
                        "source_product_key": source_key,
                        "neighbor_product_key": neighbor_key,
                        "neighbor_rank": rank,
                        "cosine_similarity": similarity,
                    }
                    for source_key, neighbor_key, rank, similarity in rows
                ],
            )
        return len(rows)


def _build_postgres_search_statement(filters: RetrievalFilters) -> Select[tuple[object, ...]]:
    semantic_distance = product_embeddings.c.embedding_vector.cosine_distance(
        _QUERY_VECTOR_BINDPARAM
    ).label("semantic_distance")
    search_text = _build_search_text_expression()
    statement = (
        select(
            products_canonical.c.canonical_product_key,
            products_canonical.c.product_name,
            products_canonical.c.product_type,
            products_canonical.c.description_text,
            product_embeddings.c.embedded_text,
            products_canonical.c.main_category,
            products_canonical.c.sub_category,
            products_canonical.c.dimensions_text,
            products_canonical.c.width_cm,
            products_canonical.c.depth_cm,
            products_canonical.c.height_cm,
            products_canonical.c.price_eur,
            products_canonical.c.url,
            products_canonical.c.display_title,
            semantic_distance,
        )
        .select_from(
            product_embeddings.join(
                products_canonical,
                product_embeddings.c.canonical_product_key
                == products_canonical.c.canonical_product_key,
            )
        )
        .where(
            products_canonical.c.country == _DEFAULT_COUNTRY,
            product_embeddings.c.embedding_model == bindparam("embedding_model"),
        )
    )

    if filters.category is not None:
        statement = statement.where(products_canonical.c.main_category == bindparam("category"))

    statement = _apply_numeric_filters(statement=statement, filters=filters)

    if filters.include_keyword is not None:
        statement = statement.where(search_text.contains(bindparam("include_keyword")))
    if filters.exclude_keyword is not None:
        statement = statement.where(~search_text.contains(bindparam("exclude_keyword")))

    return statement.order_by(*_search_order_by(filters.sort, semantic_distance)).limit(
        bindparam("result_limit")
    )


def _build_postgres_neighbor_similarity_statement() -> Select[Any]:
    source_embeddings = product_embeddings.alias("source_embeddings")
    neighbor_embeddings = product_embeddings.alias("neighbor_embeddings")
    return (
        select(
            source_embeddings.c.canonical_product_key.label("source_product_key"),
            neighbor_embeddings.c.canonical_product_key.label("neighbor_product_key"),
            (
                1.0
                - source_embeddings.c.embedding_vector.cosine_distance(
                    neighbor_embeddings.c.embedding_vector
                )
            ).label("cosine_similarity"),
        )
        .select_from(
            source_embeddings.join(
                neighbor_embeddings,
                and_(
                    source_embeddings.c.embedding_model == neighbor_embeddings.c.embedding_model,
                    source_embeddings.c.canonical_product_key
                    != neighbor_embeddings.c.canonical_product_key,
                ),
            )
        )
        .where(
            source_embeddings.c.embedding_model == bindparam("embedding_model"),
            source_embeddings.c.canonical_product_key.in_(bindparam("source_keys", expanding=True)),
            neighbor_embeddings.c.canonical_product_key.in_(
                bindparam("neighbor_keys", expanding=True)
            ),
        )
    )


def _apply_numeric_filters(
    *,
    statement: Select[tuple[object, ...]],
    filters: RetrievalFilters,
) -> Select[tuple[object, ...]]:
    price = filters.price
    dimensions = filters.dimensions
    filter_clauses: tuple[tuple[float | None, ColumnElement[bool]], ...] = (
        (price.min_eur, products_canonical.c.price_eur >= bindparam("price_min_eur")),
        (price.max_eur, products_canonical.c.price_eur <= bindparam("price_max_eur")),
        (
            dimensions.width.exact_cm,
            products_canonical.c.width_cm == bindparam("width_exact_cm"),
        ),
        (
            dimensions.depth.exact_cm,
            products_canonical.c.depth_cm == bindparam("depth_exact_cm"),
        ),
        (
            dimensions.height.exact_cm,
            products_canonical.c.height_cm == bindparam("height_exact_cm"),
        ),
        (dimensions.width.min_cm, products_canonical.c.width_cm >= bindparam("width_min_cm")),
        (dimensions.width.max_cm, products_canonical.c.width_cm <= bindparam("width_max_cm")),
        (dimensions.depth.min_cm, products_canonical.c.depth_cm >= bindparam("depth_min_cm")),
        (dimensions.depth.max_cm, products_canonical.c.depth_cm <= bindparam("depth_max_cm")),
        (
            dimensions.height.min_cm,
            products_canonical.c.height_cm >= bindparam("height_min_cm"),
        ),
        (
            dimensions.height.max_cm,
            products_canonical.c.height_cm <= bindparam("height_max_cm"),
        ),
    )
    for value, clause in filter_clauses:
        if value is not None:
            statement = statement.where(clause)
    return statement


def _search_order_by(
    sort_mode: str,
    semantic_distance: ColumnElement[float],
) -> tuple[ColumnElement[Any], ...]:
    if sort_mode == "price_asc":
        return (
            products_canonical.c.price_eur.asc().nulls_last(),
            semantic_distance.asc(),
            products_canonical.c.canonical_product_key.asc(),
        )
    if sort_mode == "price_desc":
        return (
            products_canonical.c.price_eur.desc().nulls_last(),
            semantic_distance.asc(),
            products_canonical.c.canonical_product_key.asc(),
        )
    if sort_mode == "size":
        return (
            _size_volume_expression().desc(),
            semantic_distance.asc(),
            products_canonical.c.canonical_product_key.asc(),
        )
    return (
        semantic_distance.asc(),
        products_canonical.c.canonical_product_key.asc(),
    )


def _build_search_text_expression() -> ColumnElement[str]:
    return func.lower(
        func.coalesce(products_canonical.c.product_name, "")
        + " "
        + func.coalesce(products_canonical.c.description_text, "")
        + " "
        + func.coalesce(products_canonical.c.main_category, "")
        + " "
        + func.coalesce(products_canonical.c.sub_category, "")
        + " "
        + func.coalesce(product_embeddings.c.embedded_text, "")
    )


def _size_volume_expression() -> ColumnElement[float]:
    return (
        func.coalesce(products_canonical.c.width_cm, 0.0)
        * func.coalesce(products_canonical.c.depth_cm, 0.0)
        * func.coalesce(products_canonical.c.height_cm, 0.0)
    )


def _build_legacy_hydration_statement(filters: RetrievalFilters) -> Select[tuple[object, ...]]:
    search_text = _build_search_text_expression()
    statement = (
        select(
            products_canonical.c.canonical_product_key,
            products_canonical.c.product_name,
            products_canonical.c.product_type,
            products_canonical.c.description_text,
            product_embeddings.c.embedded_text,
            products_canonical.c.main_category,
            products_canonical.c.sub_category,
            products_canonical.c.dimensions_text,
            products_canonical.c.width_cm,
            products_canonical.c.depth_cm,
            products_canonical.c.height_cm,
            products_canonical.c.price_eur,
            products_canonical.c.url,
            products_canonical.c.display_title,
        )
        .select_from(
            products_canonical.outerjoin(
                product_embeddings,
                product_embeddings.c.canonical_product_key
                == products_canonical.c.canonical_product_key,
            )
        )
        .where(
            products_canonical.c.country == _DEFAULT_COUNTRY,
            products_canonical.c.canonical_product_key.in_(
                bindparam("candidate_keys", expanding=True)
            ),
        )
    )
    statement = _apply_numeric_filters(statement=statement, filters=filters)
    if filters.category is not None:
        statement = statement.where(products_canonical.c.main_category == bindparam("category"))
    if filters.include_keyword is not None:
        statement = statement.where(search_text.contains(bindparam("include_keyword")))
    if filters.exclude_keyword is not None:
        statement = statement.where(~search_text.contains(bindparam("exclude_keyword")))
    return statement


def _legacy_result_sort_key(
    *,
    result: RetrievalResult,
    sort_mode: str,
    candidate_rank: int,
) -> tuple[float, int] | tuple[int, int] | tuple[float, int, str]:
    if sort_mode == "price_asc":
        return (
            result.price_eur if result.price_eur is not None else float("inf"),
            candidate_rank,
        )
    if sort_mode == "price_desc":
        return (
            -(result.price_eur if result.price_eur is not None else float("-inf")),
            candidate_rank,
        )
    if sort_mode == "size":
        return (
            -((result.width_cm or 0.0) * (result.depth_cm or 0.0) * (result.height_cm or 0.0)),
            candidate_rank,
            result.canonical_product_key,
        )
    return (-result.semantic_score, candidate_rank, result.canonical_product_key)


def _filter_params(filters: RetrievalFilters) -> dict[str, object]:
    return {
        "category": filters.category,
        "price_min_eur": filters.price.min_eur,
        "price_max_eur": filters.price.max_eur,
        "width_exact_cm": filters.dimensions.width.exact_cm,
        "depth_exact_cm": filters.dimensions.depth.exact_cm,
        "height_exact_cm": filters.dimensions.height.exact_cm,
        "width_min_cm": filters.dimensions.width.min_cm,
        "width_max_cm": filters.dimensions.width.max_cm,
        "depth_min_cm": filters.dimensions.depth.min_cm,
        "depth_max_cm": filters.dimensions.depth.max_cm,
        "height_min_cm": filters.dimensions.height.min_cm,
        "height_max_cm": filters.dimensions.height.max_cm,
        "include_keyword": filters.include_keyword.lower() if filters.include_keyword else None,
        "exclude_keyword": filters.exclude_keyword.lower() if filters.exclude_keyword else None,
    }


def _compute_neighbor_similarities_from_embeddings(
    *,
    engine: Engine,
    embedding_model: str,
    product_keys: Sequence[str],
) -> dict[tuple[str, str], float]:
    normalized_keys = [key for key in dict.fromkeys(product_keys) if key]
    if len(normalized_keys) < _MIN_PAIRWISE_KEY_COUNT:
        return {}
    with engine.connect() as connection:
        rows = connection.execute(
            _READ_EMBEDDINGS_FOR_SIMILARITY_QUERY,
            {
                "embedding_model": embedding_model,
                "product_keys": normalized_keys,
            },
        ).fetchall()
    vectors_by_key = {
        str(row[0]): _normalize_vector(_vector_from_value(row[1]))
        for row in rows
        if row[1] is not None
    }
    lookup: dict[tuple[str, str], float] = {}
    for source_key in normalized_keys:
        source_vector = vectors_by_key.get(source_key)
        if not source_vector:
            continue
        for neighbor_key in normalized_keys:
            if source_key == neighbor_key:
                continue
            neighbor_vector = vectors_by_key.get(neighbor_key)
            if not neighbor_vector:
                continue
            lookup[(source_key, neighbor_key)] = _cosine_similarity(
                source_vector=source_vector,
                neighbor_vector=neighbor_vector,
            )
    return lookup


def _rank_embedding_rows(
    *,
    rows: Sequence[tuple[str, str, tuple[float, ...]]],
    query_vector: tuple[float, ...],
    result_limit: int,
) -> list[VectorMatch]:
    normalized_query = _normalize_vector(query_vector)
    if not normalized_query or result_limit <= 0:
        return []

    scored_matches: list[VectorMatch] = []
    for canonical_product_key, _embedding_model, vector in rows:
        normalized_vector = _normalize_vector(vector)
        if not normalized_vector:
            continue
        scored_matches.append(
            VectorMatch(
                canonical_product_key=canonical_product_key,
                semantic_score=_cosine_similarity(
                    source_vector=normalized_query,
                    neighbor_vector=normalized_vector,
                ),
            )
        )
    scored_matches.sort(
        key=lambda item: (-item.semantic_score, item.canonical_product_key),
    )
    return scored_matches[:result_limit]


def _search_row_to_result(row: Row[tuple[object, ...]]) -> RetrievalResult:
    mapping = row._mapping
    semantic_distance = _float_or_none(mapping["semantic_distance"])
    if semantic_distance is None:
        semantic_distance = 1.0
    semantic_score = max(0.0, 1.0 - semantic_distance)
    return RetrievalResult(
        canonical_product_key=str(mapping["canonical_product_key"]),
        product_name=str(mapping["product_name"]),
        product_type=_str_or_none(mapping["product_type"]),
        description_text=_str_or_none(mapping["description_text"]),
        embedding_text=_format_embedding_text(mapping["embedded_text"]),
        main_category=_str_or_none(mapping["main_category"]),
        sub_category=_str_or_none(mapping["sub_category"]),
        dimensions_text=_str_or_none(mapping["dimensions_text"]),
        width_cm=_float_or_none(mapping["width_cm"]),
        depth_cm=_float_or_none(mapping["depth_cm"]),
        height_cm=_float_or_none(mapping["height_cm"]),
        price_eur=_float_or_none(mapping["price_eur"]),
        url=_str_or_none(mapping["url"]),
        semantic_score=semantic_score,
        filter_pass_reasons=("structured_filters_passed",),
        rank_explanation=f"pgvector cosine score {semantic_score:.3f}",
        display_title=_str_or_none(mapping["display_title"]),
    )


def _legacy_row_to_result(
    row: Sequence[object],
    *,
    semantic_score: float,
) -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key=str(row[0]),
        product_name=str(row[1]),
        product_type=_str_or_none(row[2]),
        description_text=_str_or_none(row[3]),
        embedding_text=_format_embedding_text(row[4]),
        main_category=_str_or_none(row[5]),
        sub_category=_str_or_none(row[6]),
        dimensions_text=_str_or_none(row[7]),
        width_cm=_float_or_none(row[8]),
        depth_cm=_float_or_none(row[9]),
        height_cm=_float_or_none(row[10]),
        price_eur=_float_or_none(row[11]),
        url=_str_or_none(row[12]),
        semantic_score=semantic_score,
        filter_pass_reasons=("structured_filters_passed",),
        rank_explanation=f"legacy cosine score {semantic_score:.3f}",
        display_title=_str_or_none(row[13]),
    )


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _image_order_priority(column: object) -> ColumnElement[int]:
    expression = cast("Any", column)
    return case((expression.is_(True), 0), else_=1)


def _format_embedding_text(value: object) -> str | None:
    text_value = _str_or_none(value)
    if text_value is None:
        return None
    return text_value.replace("\\n", "\n")


def _vector_from_value(value: object) -> tuple[float, ...]:
    if value is None:
        return ()
    if hasattr(value, "tolist"):
        return _vector_from_value(value.tolist())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(float(item) for item in value if isinstance(item, int | float))
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            items = [part.strip() for part in stripped[1:-1].split(",") if part.strip()]
            return tuple(float(item) for item in items)
    return ()


def _normalize_vector(vector: tuple[float, ...]) -> tuple[float, ...]:
    if not vector:
        return ()
    norm = sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return tuple(0.0 for _ in vector)
    return tuple(value / norm for value in vector)


def _cosine_similarity(
    *,
    source_vector: tuple[float, ...],
    neighbor_vector: tuple[float, ...],
) -> float:
    length = min(len(source_vector), len(neighbor_vector))
    if length == 0:
        return 0.0
    return float(sum(source_vector[index] * neighbor_vector[index] for index in range(length)))
