"""Persistence helpers for evaluation query and metric data."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

import duckdb


class EvalRepository:
    """DB operations for eval query generation and metric snapshots."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def upsert_prompt(self, prompt_version: str, prompt_text: str, prompt_hash: str) -> None:
        """Create or replace a prompt registry row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.eval_prompt_registry (
                prompt_version,
                prompt_text,
                prompt_hash,
                created_at
            ) VALUES (?, ?, ?, now())
            """,
            [prompt_version, prompt_text, prompt_hash],
        )

    def upsert_subset(self, subset_id: str, subset_definition: str, subset_hash: str) -> None:
        """Create or replace an eval subset registry row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.eval_subset_registry (
                subset_id,
                subset_definition,
                subset_hash,
                source_snapshot_ts,
                created_at
            ) VALUES (?, ?, ?, ?, now())
            """,
            [subset_id, subset_definition, subset_hash, datetime.now(UTC)],
        )

    def insert_generated_queries(
        self,
        prompt_version: str,
        subset_id: str,
        rows: Sequence[tuple[str, str, str | None, str | None]],
    ) -> None:
        """Persist generated eval queries with deterministic IDs."""

        self._connection.executemany(
            """
            INSERT OR REPLACE INTO app.eval_queries_generated (
                eval_query_id,
                prompt_version,
                subset_id,
                query_text,
                category_hint,
                intent_kind,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, now())
            """,
            [(row[0], prompt_version, subset_id, row[1], row[2], row[3]) for row in rows],
        )

    def get_labeled_queries(self) -> list[tuple[str, str, list[str]]]:
        """Return query text with expected top labels."""

        rows = self._connection.execute(
            """
            SELECT
                q.eval_query_id,
                q.query_text,
                l.canonical_product_key,
                l.relevance_rank
            FROM app.eval_queries_generated AS q
            JOIN app.eval_labels AS l
              ON l.eval_query_id = q.eval_query_id
            ORDER BY q.eval_query_id, l.relevance_rank ASC
            """
        ).fetchall()

        grouped_queries: dict[str, str] = {}
        grouped_labels: dict[str, list[str]] = defaultdict(list)
        for eval_query_id, query_text, canonical_key, _ in rows:
            query_id = str(eval_query_id)
            grouped_queries[query_id] = str(query_text)
            grouped_labels[query_id].append(str(canonical_key))

        return [
            (query_id, grouped_queries[query_id], grouped_labels[query_id])
            for query_id in grouped_queries
        ]

    def insert_eval_run(
        self,
        eval_run_id: str,
        index_run_id: str,
        strategy_version: str,
        embedding_model: str,
        k: int,
        hit_at_k: float,
        recall_at_k: float,
        mrr: float,
    ) -> None:
        """Persist metric snapshot from one evaluation run."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.eval_runs (
                eval_run_id,
                index_run_id,
                strategy_version,
                embedding_model,
                k,
                hit_at_k,
                recall_at_k,
                mrr,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                eval_run_id,
                index_run_id,
                strategy_version,
                embedding_model,
                k,
                hit_at_k,
                recall_at_k,
                mrr,
            ],
        )
