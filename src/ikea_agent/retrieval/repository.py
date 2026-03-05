"""DuckDB repositories for retrieval hydration and shortlist persistence."""

from __future__ import annotations

from collections.abc import Sequence

import duckdb

from ikea_agent.retrieval.vector_store import VectorMatch
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult, ShortlistItem


class RetrievalRepository:
    """Hydrate Milvus candidates with catalog data and persist query logs."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def read_embedding_rows(self, embedding_model: str) -> list[tuple[str, str, tuple[float, ...]]]:
        """Read embedding rows used to build the Milvus Lite collection."""

        rows = self._connection.execute(
            """
            SELECT
                canonical_product_key,
                embedding_model,
                embedding_vector
            FROM app.product_embeddings
            WHERE embedding_model = ?
            ORDER BY canonical_product_key
            """,
            [embedding_model],
        ).fetchall()

        return [
            (str(row[0]), str(row[1]), _vector_from_value(row[2]))
            for row in rows
            if row[2] is not None
        ]

    def hydrate_candidates(
        self,
        *,
        candidates: Sequence[VectorMatch],
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        """Apply structured filters and hydrate vector hits with product metadata."""

        if not candidates:
            return []

        self._connection.execute(
            """
            CREATE OR REPLACE TEMP TABLE temp_candidate_scores (
                canonical_product_key VARCHAR,
                semantic_score DOUBLE,
                candidate_rank BIGINT
            )
            """
        )
        self._connection.executemany(
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

        query = _hydration_query(filters.sort)
        params = [*list(_filter_params(filters)), result_limit]
        rows = self._connection.execute(query, params).fetchall()

        return [
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
                semantic_score=float(row[13]),
                filter_pass_reasons=("structured_filters_passed",),
                rank_explanation=f"milvus cosine score {float(row[13]):.3f}",
            )
            for row in rows
        ]

    def log_query(
        self,
        query_id: str,
        query_text: str,
        filters: RetrievalFilters,
        result_limit: int,
        low_confidence: bool,
        latency_ms: int,
        source: str,
    ) -> None:
        """Persist one query request for debugging and analysis."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.query_log (
                query_id,
                query_text,
                sort_mode,
                include_keyword,
                exclude_keyword,
                result_limit,
                category_filter,
                min_price_eur,
                max_price_eur,
                min_width_cm,
                max_width_cm,
                min_depth_cm,
                max_depth_cm,
                min_height_cm,
                max_height_cm,
                exact_width_cm,
                exact_depth_cm,
                exact_height_cm,
                low_confidence,
                request_source,
                latency_ms,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                query_id,
                query_text,
                filters.sort,
                filters.include_keyword,
                filters.exclude_keyword,
                result_limit,
                filters.category,
                filters.price.min_eur,
                filters.price.max_eur,
                filters.dimensions.width.min_cm,
                filters.dimensions.width.max_cm,
                filters.dimensions.depth.min_cm,
                filters.dimensions.depth.max_cm,
                filters.dimensions.height.min_cm,
                filters.dimensions.height.max_cm,
                filters.dimensions.width.exact_cm,
                filters.dimensions.depth.exact_cm,
                filters.dimensions.height.exact_cm,
                low_confidence,
                source,
                latency_ms,
            ],
        )


class ShortlistRepository:
    """Persistence operations for global shortlist state."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def add(self, canonical_product_key: str, note: str | None = None) -> None:
        """Insert or update one global shortlist item."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.shortlist_global (
                canonical_product_key,
                added_at,
                note
            ) VALUES (?, now(), ?)
            """,
            [canonical_product_key, note],
        )

    def remove(self, canonical_product_key: str) -> None:
        """Delete one shortlist item by canonical key."""

        self._connection.execute(
            "DELETE FROM app.shortlist_global WHERE canonical_product_key = ?",
            [canonical_product_key],
        )

    def list_items(self) -> list[ShortlistItem]:
        """Load hydrated shortlist entries from canonical catalog table."""

        rows = self._connection.execute(
            """
            SELECT
                p.canonical_product_key,
                p.product_name,
                p.product_type,
                p.main_category,
                p.sub_category,
                p.dimensions_text,
                p.price_eur,
                p.url,
                p.country,
                s.note
            FROM app.shortlist_global AS s
            JOIN app.products_canonical AS p
            ON p.canonical_product_key = s.canonical_product_key
            WHERE p.country = 'Germany'
            ORDER BY s.added_at DESC
            """
        ).fetchall()
        return [
            ShortlistItem(
                canonical_product_key=str(row[0]),
                product_name=str(row[1]),
                product_type=_str_or_none(row[2]),
                main_category=_str_or_none(row[3]),
                sub_category=_str_or_none(row[4]),
                dimensions_text=_str_or_none(row[5]),
                price_eur=_float_or_none(row[6]),
                url=_str_or_none(row[7]),
                note=_str_or_none(row[9]),
            )
            for row in rows
        ]


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
