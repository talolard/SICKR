"""SQLAlchemy-backed catalog hydration repository for vector search candidates."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from typing import cast

from sqlalchemy import Engine, bindparam, select, text

from ikea_agent.retrieval.schema import product_embeddings
from ikea_agent.retrieval.service import VectorMatch
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult

_MIN_PAIRWISE_KEY_COUNT = 2
_NEIGHBOR_SIMILARITIES_QUERY = text(
    """
    SELECT source_product_key, neighbor_product_key, cosine_similarity
    FROM catalog.product_embedding_neighbors
    WHERE embedding_model = :embedding_model
      AND source_product_key IN :source_keys
      AND neighbor_product_key IN :neighbor_keys
    """
).bindparams(
    bindparam("source_keys", expanding=True),
    bindparam("neighbor_keys", expanding=True),
)
_READ_PRODUCT_BY_KEY_QUERY = text(
    """
    SELECT
        c.canonical_product_key,
        c.product_name,
        c.product_type,
        c.description_text,
        e.embedded_text,
        c.main_category,
        c.sub_category,
        c.dimensions_text,
        c.width_cm,
        c.depth_cm,
        c.height_cm,
        c.price_eur,
        c.url,
        c.display_title
    FROM catalog.products_canonical AS c
    LEFT JOIN catalog.product_embeddings AS e
      ON e.canonical_product_key = c.canonical_product_key
    WHERE c.country = 'Germany'
      AND c.canonical_product_key = :canonical_product_key
    LIMIT 1
    """
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
_DELETE_NEIGHBOR_ROWS_QUERY = text(
    """
    DELETE FROM catalog.product_embedding_neighbors
    WHERE embedding_model = :embedding_model
    """
)
_INSERT_NEIGHBOR_ROWS_QUERY = text(
    """
    INSERT INTO catalog.product_embedding_neighbors (
        embedding_model,
        source_product_key,
        neighbor_product_key,
        neighbor_rank,
        cosine_similarity
    ) VALUES (
        :embedding_model,
        :source_product_key,
        :neighbor_product_key,
        :neighbor_rank,
        :cosine_similarity
    )
    """
)
_READ_EMBEDDINGS_FOR_SIMILARITY_QUERY = select(
    product_embeddings.c.canonical_product_key,
    product_embeddings.c.embedding_vector,
).where(
    product_embeddings.c.embedding_model == bindparam("embedding_model"),
    product_embeddings.c.canonical_product_key.in_(bindparam("product_keys", expanding=True)),
)


class CatalogRepository:
    """Hydrate semantic candidate keys with typed product rows."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

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

        rows: list[tuple[object, ...]]
        with self._engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS temp_candidate_scores"))
            connection.execute(
                text(
                    """
                    CREATE TEMPORARY TABLE temp_candidate_scores (
                        canonical_product_key VARCHAR,
                        semantic_score DOUBLE PRECISION,
                        candidate_rank BIGINT
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO temp_candidate_scores (
                        canonical_product_key,
                        semantic_score,
                        candidate_rank
                    ) VALUES (
                        :canonical_product_key,
                        :semantic_score,
                        :candidate_rank
                    )
                    """
                ),
                [
                    {
                        "canonical_product_key": item.canonical_product_key,
                        "semantic_score": item.semantic_score,
                        "candidate_rank": rank,
                    }
                    for rank, item in enumerate(candidates, start=1)
                ],
            )
            rows = cast(
                "list[tuple[object, ...]]",
                connection.execute(
                    text(_hydration_query(filters.sort)),
                    {
                        **_filter_params(filters),
                        "result_limit": result_limit,
                    },
                ).fetchall(),
            )

        hydrated_results: list[RetrievalResult] = []
        for row in rows:
            semantic_score = _float_or_none(row[14])
            if semantic_score is None:
                continue
            hydrated_results.append(
                RetrievalResult(
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
                    rank_explanation=f"milvus cosine score {semantic_score:.3f}",
                    display_title=_str_or_none(row[13]),
                )
            )
        return hydrated_results

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

        with self._engine.connect() as connection:
            rows = cast(
                "list[tuple[object, ...]]",
                connection.execute(
                    _NEIGHBOR_SIMILARITIES_QUERY,
                    {
                        "embedding_model": embedding_model,
                        "source_keys": normalized_keys,
                        "neighbor_keys": normalized_keys,
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
            product_keys=normalized_keys,
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


class EmbeddingSnapshotRepository:
    """Load embedding snapshot rows for shared Milvus preparation scripts."""

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
            connection.execute(_DELETE_NEIGHBOR_ROWS_QUERY, {"embedding_model": embedding_model})
            if not rows:
                return 0
            connection.execute(
                _INSERT_NEIGHBOR_ROWS_QUERY,
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


def _hydration_query(sort_mode: str) -> str:
    order_by = "ORDER BY t.semantic_score DESC, t.candidate_rank ASC"
    if sort_mode == "price_asc":
        order_by = "ORDER BY c.price_eur ASC NULLS LAST, t.candidate_rank ASC"
    elif sort_mode == "price_desc":
        order_by = "ORDER BY c.price_eur DESC NULLS LAST, t.candidate_rank ASC"
    elif sort_mode == "size":
        order_by = (
            "ORDER BY (coalesce(c.width_cm, 0) * coalesce(c.depth_cm, 0) * "
            "coalesce(c.height_cm, 0)) DESC NULLS LAST, t.candidate_rank ASC"
        )

    query = """
        SELECT
            c.canonical_product_key,
            c.product_name,
            c.product_type,
            c.description_text,
            e.embedded_text,
            c.main_category,
            c.sub_category,
            c.dimensions_text,
            c.width_cm,
            c.depth_cm,
            c.height_cm,
            c.price_eur,
            c.url,
            c.display_title,
            t.semantic_score
        FROM temp_candidate_scores AS t
        JOIN catalog.products_canonical AS c
          ON c.canonical_product_key = t.canonical_product_key
        LEFT JOIN catalog.product_embeddings AS e
          ON e.canonical_product_key = c.canonical_product_key
        WHERE c.country = 'Germany'
          AND (:category IS NULL OR c.main_category = :category)
          AND (
            :price_min_eur IS NULL
            OR c.price_eur IS NOT NULL AND c.price_eur >= :price_min_eur
          )
          AND (
            :price_max_eur IS NULL
            OR c.price_eur IS NOT NULL AND c.price_eur <= :price_max_eur
          )
          AND (:width_exact_cm IS NULL OR c.width_cm = :width_exact_cm)
          AND (:depth_exact_cm IS NULL OR c.depth_cm = :depth_exact_cm)
          AND (:height_exact_cm IS NULL OR c.height_cm = :height_exact_cm)
          AND (:width_min_cm IS NULL OR c.width_cm IS NOT NULL AND c.width_cm >= :width_min_cm)
          AND (:width_max_cm IS NULL OR c.width_cm IS NOT NULL AND c.width_cm <= :width_max_cm)
          AND (:depth_min_cm IS NULL OR c.depth_cm IS NOT NULL AND c.depth_cm >= :depth_min_cm)
          AND (:depth_max_cm IS NULL OR c.depth_cm IS NOT NULL AND c.depth_cm <= :depth_max_cm)
          AND (
            :height_min_cm IS NULL
            OR c.height_cm IS NOT NULL AND c.height_cm >= :height_min_cm
          )
          AND (
            :height_max_cm IS NULL
            OR c.height_cm IS NOT NULL AND c.height_cm <= :height_max_cm
          )
          AND (
            :include_keyword IS NULL
            OR strpos(
              lower(
                concat_ws(
                  ' ',
                  c.product_name,
                  coalesce(c.description_text, ''),
                  coalesce(c.main_category, ''),
                  coalesce(c.sub_category, ''),
                  coalesce(e.embedded_text, '')
                )
              ),
              lower(:include_keyword)
            ) > 0
          )
          AND (
            :exclude_keyword IS NULL
            OR strpos(
              lower(
                concat_ws(
                  ' ',
                  c.product_name,
                  coalesce(c.description_text, ''),
                  coalesce(c.main_category, ''),
                  coalesce(c.sub_category, ''),
                  coalesce(e.embedded_text, '')
                )
              ),
              lower(:exclude_keyword)
            ) = 0
          )
    """
    return query + order_by + " LIMIT :result_limit"


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
        "include_keyword": filters.include_keyword,
        "exclude_keyword": filters.exclude_keyword,
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
