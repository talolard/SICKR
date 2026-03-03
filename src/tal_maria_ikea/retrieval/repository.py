"""DuckDB-backed retrieval and shortlist repositories."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb

from tal_maria_ikea.shared.types import RetrievalFilters, RetrievalResult, ShortlistItem


class RetrievalRepository:
    """Run retrieval SQL and persist request logs."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection
        self._retrieval_sql = Path("sql/31_retrieval_candidates.sql").read_text(encoding="utf-8")

    def search(
        self,
        query_vector: Sequence[float],
        embedding_model: str,
        strategy_version: str,
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        """Search catalog vectors and apply structured filters."""

        params = [
            list(query_vector),
            embedding_model,
            strategy_version,
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
            result_limit,
        ]

        rows = self._connection.execute(
            self._retrieval_sql,
            params,
        ).fetchall()

        results: list[RetrievalResult] = []
        for row in rows:
            score = float(row[12])
            results.append(
                RetrievalResult(
                    canonical_product_key=str(row[0]),
                    product_name=str(row[1]),
                    product_type=_str_or_none(row[2]),
                    description_text=_str_or_none(row[3]),
                    main_category=_str_or_none(row[4]),
                    sub_category=_str_or_none(row[5]),
                    dimensions_text=_str_or_none(row[6]),
                    width_cm=_float_or_none(row[7]),
                    depth_cm=_float_or_none(row[8]),
                    height_cm=_float_or_none(row[9]),
                    price_eur=_float_or_none(row[10]),
                    url=_str_or_none(row[11]),
                    semantic_score=score,
                    filter_pass_reasons=("structured_filters_passed",),
                    rank_explanation=f"semantic cosine score {score:.3f}",
                )
            )

        return results

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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                query_id,
                query_text,
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
        self._shortlist_sql = Path("sql/32_shortlist.sql").read_text(encoding="utf-8")

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
        """Load hydrated shortlist entries from retrieval view."""

        rows = self._connection.execute(self._shortlist_sql).fetchall()
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


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None
