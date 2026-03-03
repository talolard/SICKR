"""DuckDB repository for embedding indexing workflows."""

from __future__ import annotations

from collections.abc import Sequence

import duckdb

from tal_maria_ikea.shared.types import EmbeddedVectorRow


class IndexRepository:
    """Persistence and loading operations used by the indexing pipeline."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def read_embedding_inputs(
        self, view_name: str, subset_limit: int | None
    ) -> list[tuple[str, str]]:
        """Load canonical key and text payload rows from a strategy view."""

        if view_name not in {
            "app.embedding_input_v1_baseline",
            "app.embedding_input_v2_metadata_first",
        }:
            message = f"Unsupported embedding input view: {view_name}"
            raise ValueError(message)

        if view_name == "app.embedding_input_v1_baseline":
            query = (
                "SELECT canonical_product_key, embedding_text "
                "FROM app.embedding_input_v1_baseline "
                "ORDER BY canonical_product_key"
            )
        else:
            query = (
                "SELECT canonical_product_key, embedding_text "
                "FROM app.embedding_input_v2_metadata_first "
                "ORDER BY canonical_product_key"
            )
        if subset_limit is not None:
            query += " LIMIT ?"
            rows = self._connection.execute(query, [subset_limit]).fetchall()
        else:
            rows = self._connection.execute(query).fetchall()

        return [(str(row[0]), str(row[1])) for row in rows]

    def insert_run(
        self,
        run_id: str,
        scope: str,
        strategy_version: str,
        embedding_model: str,
        provider: str,
        use_batch: bool,
        subset_limit: int | None,
        requested_parallelism: int,
        total_records: int,
    ) -> None:
        """Persist a new run metadata row with running status."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.embedding_runs (
                run_id,
                scope,
                strategy_version,
                embedding_model,
                provider,
                use_batch,
                subset_limit,
                requested_parallelism,
                status,
                total_records,
                embedded_records,
                failed_records,
                started_at,
                completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, 0, 0, now(), NULL)
            """,
            [
                run_id,
                scope,
                strategy_version,
                embedding_model,
                provider,
                use_batch,
                subset_limit,
                requested_parallelism,
                total_records,
            ],
        )

    def upsert_embeddings(
        self,
        rows: Sequence[EmbeddedVectorRow],
        embedding_model: str,
        run_id: str,
    ) -> None:
        """Write embedding vectors in upsert mode keyed by product/model/strategy."""

        payload = [
            (
                row.canonical_product_key,
                embedding_model,
                row.strategy_version,
                run_id,
                _to_fixed_vector(row.embedding_vector, dimensions=3072),
                row.embedding_text,
            )
            for row in rows
        ]
        self._connection.executemany(
            """
            INSERT OR REPLACE INTO app.product_embeddings (
                canonical_product_key,
                embedding_model,
                strategy_version,
                run_id,
                embedding_vector,
                embedded_text,
                embedded_at
            ) VALUES (?, ?, ?, ?, CAST(? AS FLOAT[3072]), ?, now())
            """,
            payload,
        )

    def mark_run_complete(self, run_id: str, embedded_records: int, failed_records: int) -> None:
        """Finalize run metadata after indexing finishes."""

        self._connection.execute(
            """
            UPDATE app.embedding_runs
            SET status = 'completed',
                embedded_records = ?,
                failed_records = ?,
                completed_at = now()
            WHERE run_id = ?
            """,
            [embedded_records, failed_records, run_id],
        )

    def create_vss_hnsw_index(self, metric: str = "cosine") -> None:
        """Create or refresh HNSW index for embedding vectors.

        This uses DuckDB's experimental `vss` extension and enables persistence mode
        for local disk-backed databases.
        """

        self._connection.execute("INSTALL vss")
        self._connection.execute("LOAD vss")
        self._connection.execute("SET hnsw_enable_experimental_persistence = true")
        if metric not in {"cosine", "l2sq", "ip"}:
            message = f"Unsupported VSS metric: {metric}"
            raise ValueError(message)
        if metric == "cosine":
            metric_sql = "cosine"
        elif metric == "l2sq":
            metric_sql = "l2sq"
        else:
            metric_sql = "ip"
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_embeddings_hnsw "
            "ON app.product_embeddings USING HNSW (embedding_vector) "
            f"WITH (metric = '{metric_sql}')"
        )


def _to_fixed_vector(vector: Sequence[float], dimensions: int) -> list[float]:
    values = [float(value) for value in vector[:dimensions]]
    if len(values) < dimensions:
        values.extend([0.0] * (dimensions - len(values)))
    return values
