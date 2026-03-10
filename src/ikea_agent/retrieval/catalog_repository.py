"""SQLAlchemy-backed catalog hydration repository for vector search candidates."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Engine, bindparam, text

from ikea_agent.retrieval.service import VectorMatch
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult

_MIN_PAIRWISE_KEY_COUNT = 2


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
        """Apply filters and hydrate vector hits with product metadata."""

        if not candidates:
            return []

        rows: list[tuple[object, ...]]
        with self._engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS temp_candidate_scores")
            connection.exec_driver_sql(
                """
                CREATE TEMP TABLE temp_candidate_scores (
                    canonical_product_key VARCHAR,
                    semantic_score DOUBLE,
                    candidate_rank BIGINT
                )
                """
            )
            connection.exec_driver_sql(
                """
                INSERT INTO temp_candidate_scores (
                    canonical_product_key,
                    semantic_score,
                    candidate_rank
                ) VALUES (?, ?, ?)
                """,
                [
                    (item.canonical_product_key, item.semantic_score, rank)
                    for rank, item in enumerate(candidates, start=1)
                ],
            )
            rows = cast(
                "list[tuple[object, ...]]",
                connection.exec_driver_sql(
                    _hydration_query(filters.sort),
                    (*_filter_params(filters), result_limit),
                ).fetchall(),
            )

        hydrated_results: list[RetrievalResult] = []
        for row in rows:
            semantic_score = _float_or_none(row[13])
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
                )
            )
        return hydrated_results

    def read_neighbor_similarities(
        self,
        *,
        embedding_model: str,
        product_keys: Sequence[str],
    ) -> dict[tuple[str, str], float]:
        """Read precomputed pairwise cosine similarities for a candidate key set."""

        normalized_keys = [key for key in dict.fromkeys(product_keys) if key]
        if len(normalized_keys) < _MIN_PAIRWISE_KEY_COUNT:
            return {}

        query = text(
            "SELECT source_product_key, neighbor_product_key, cosine_similarity "
            "FROM app.product_embedding_neighbors "
            "WHERE embedding_model = :embedding_model "
            "AND source_product_key IN :source_keys "
            "AND neighbor_product_key IN :neighbor_keys"
        ).bindparams(
            bindparam("source_keys", expanding=True),
            bindparam("neighbor_keys", expanding=True),
        )
        with self._engine.connect() as connection:
            rows = cast(
                "list[tuple[object, ...]]",
                connection.execute(
                    query,
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
        return lookup


class EmbeddingSnapshotRepository:
    """Load embedding snapshot rows for external Milvus hydration scripts."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def read_embedding_rows(self, embedding_model: str) -> list[tuple[str, str, tuple[float, ...]]]:
        """Read embedding rows from DuckDB snapshot tables."""

        with self._engine.connect() as connection:
            rows = connection.exec_driver_sql(
                """
                SELECT
                    canonical_product_key,
                    embedding_model,
                    embedding_vector
                FROM app.product_embeddings
                WHERE embedding_model = ?
                ORDER BY canonical_product_key
                """,
                (embedding_model,),
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
            connection.exec_driver_sql(
                "DELETE FROM app.product_embedding_neighbors WHERE embedding_model = ?",
                (embedding_model,),
            )
            if not rows:
                return 0
            connection.exec_driver_sql(
                """
                INSERT INTO app.product_embedding_neighbors (
                    embedding_model,
                    source_product_key,
                    neighbor_product_key,
                    neighbor_rank,
                    cosine_similarity
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (embedding_model, source_key, neighbor_key, rank, similarity)
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

    query = (
        "SELECT "
        "c.canonical_product_key, c.product_name, c.product_type, c.description_text, "
        "e.embedded_text, c.main_category, c.sub_category, c.dimensions_text, "
        "c.width_cm, c.depth_cm, c.height_cm, c.price_eur, c.url, t.semantic_score "
        "FROM temp_candidate_scores AS t "
        "JOIN app.products_canonical AS c "
        "ON c.canonical_product_key = t.canonical_product_key "
        "LEFT JOIN app.product_embeddings AS e "
        "ON e.canonical_product_key = c.canonical_product_key "
        "WHERE c.country = 'Germany' "
        "AND (? IS NULL OR c.main_category = ?) "
        "AND (? IS NULL OR c.price_eur IS NOT NULL AND c.price_eur >= ?) "
        "AND (? IS NULL OR c.price_eur IS NOT NULL AND c.price_eur <= ?) "
        "AND (? IS NULL OR c.width_cm = ?) "
        "AND (? IS NULL OR c.depth_cm = ?) "
        "AND (? IS NULL OR c.height_cm = ?) "
        "AND (? IS NULL OR c.width_cm IS NOT NULL AND c.width_cm >= ?) "
        "AND (? IS NULL OR c.width_cm IS NOT NULL AND c.width_cm <= ?) "
        "AND (? IS NULL OR c.depth_cm IS NOT NULL AND c.depth_cm >= ?) "
        "AND (? IS NULL OR c.depth_cm IS NOT NULL AND c.depth_cm <= ?) "
        "AND (? IS NULL OR c.height_cm IS NOT NULL AND c.height_cm >= ?) "
        "AND (? IS NULL OR c.height_cm IS NOT NULL AND c.height_cm <= ?) "
        "AND (? IS NULL OR strpos(lower(concat_ws(' ', c.product_name, "
        "coalesce(c.description_text, ''), coalesce(c.main_category, ''), "
        "coalesce(c.sub_category, ''), coalesce(e.embedded_text, ''))), lower(?)) > 0) "
        "AND (? IS NULL OR strpos(lower(concat_ws(' ', c.product_name, "
        "coalesce(c.description_text, ''), coalesce(c.main_category, ''), "
        "coalesce(c.sub_category, ''), coalesce(e.embedded_text, ''))), lower(?)) = 0) "
    )
    return query + order_by + " LIMIT ?"


def _filter_params(filters: RetrievalFilters) -> tuple[object, ...]:
    return (
        filters.category,
        filters.category,
        filters.price.min_eur,
        filters.price.min_eur,
        filters.price.max_eur,
        filters.price.max_eur,
        filters.dimensions.width.exact_cm,
        filters.dimensions.width.exact_cm,
        filters.dimensions.depth.exact_cm,
        filters.dimensions.depth.exact_cm,
        filters.dimensions.height.exact_cm,
        filters.dimensions.height.exact_cm,
        filters.dimensions.width.min_cm,
        filters.dimensions.width.min_cm,
        filters.dimensions.width.max_cm,
        filters.dimensions.width.max_cm,
        filters.dimensions.depth.min_cm,
        filters.dimensions.depth.min_cm,
        filters.dimensions.depth.max_cm,
        filters.dimensions.depth.max_cm,
        filters.dimensions.height.min_cm,
        filters.dimensions.height.min_cm,
        filters.dimensions.height.max_cm,
        filters.dimensions.height.max_cm,
        filters.include_keyword,
        filters.include_keyword,
        filters.exclude_keyword,
        filters.exclude_keyword,
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


def _format_embedding_text(value: object) -> str | None:
    text = _str_or_none(value)
    if text is None:
        return None
    return text.replace("\\n", "\n")


def _vector_from_value(value: object) -> tuple[float, ...]:
    if isinstance(value, list):
        return tuple(float(item) for item in value if isinstance(item, int | float))
    if isinstance(value, tuple):
        return tuple(float(item) for item in value if isinstance(item, int | float))
    return ()
