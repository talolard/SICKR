"""DuckDB repository for embedding indexing workflows."""

from __future__ import annotations

from collections.abc import Sequence

import duckdb

from tal_maria_ikea.shared.types import EmbeddedVectorRow


class IndexRepository:
    """Persistence and loading operations used by the indexing pipeline."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def read_embedding_inputs(self, subset_limit: int | None) -> list[tuple[str, str]]:
        """Load canonical key and text payload rows from app.embedding_input."""

        query = (
            "SELECT canonical_product_key, embedding_text "
            "FROM app.embedding_input "
            "ORDER BY canonical_product_key"
        )
        if subset_limit is not None:
            query += " LIMIT ?"
            rows = self._connection.execute(query, [subset_limit]).fetchall()
        else:
            rows = self._connection.execute(query).fetchall()

        return [(str(row[0]), str(row[1])) for row in rows]

    def embedding_vector_dimensions(self) -> int:
        """Return the fixed dimension configured for app.product_embeddings.embedding_vector."""

        row = self._connection.execute(
            """
            SELECT column_type
            FROM (DESCRIBE app.product_embeddings)
            WHERE column_name = 'embedding_vector'
            """
        ).fetchone()
        if row is None or row[0] is None:
            message = "Missing embedding_vector column in app.product_embeddings."
            raise RuntimeError(message)

        column_type = str(row[0])
        if not (column_type.startswith("FLOAT[") and column_type.endswith("]")):
            message = (
                f"Unexpected embedding_vector column type. Expected FLOAT[N], got {column_type}."
            )
            raise RuntimeError(message)

        return int(column_type.removeprefix("FLOAT[").removesuffix("]"))

    def insert_run(
        self,
        run_id: str,
        scope: str,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, 0, 0, now(), NULL)
            """,
            [
                run_id,
                scope,
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
        vector_dimensions: int,
        chunk_size: int = 25,
    ) -> None:
        """Write embedding vectors in upsert mode keyed by product/model."""

        payload = [
            (
                row.canonical_product_key,
                embedding_model,
                run_id,
                _to_fixed_vector(row.embedding_vector, dimensions=vector_dimensions),
                row.embedding_text,
            )
            for row in rows
        ]
        for start in range(0, len(payload), chunk_size):
            chunk = payload[start : start + chunk_size]
            self._upsert_payload(chunk)

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

    def drop_vss_hnsw_index_if_exists(self) -> None:
        """Drop HNSW index before bulk upserts to avoid index-maintenance overhead."""

        self._connection.execute("DROP INDEX IF EXISTS idx_product_embeddings_hnsw")

    def _upsert_payload(self, payload: Sequence[tuple[object, ...]]) -> None:
        """Execute embedding upsert with one retry after loading vss extension."""

        upsert_sql = (
            "INSERT OR REPLACE INTO app.product_embeddings ("
            "canonical_product_key, embedding_model, run_id, "
            "embedding_vector, embedded_text, embedded_at"
            ") VALUES (?, ?, ?, ?, ?, now())"
        )
        try:
            self._connection.executemany(upsert_sql, payload)
        except duckdb.Error as error:
            if "unknown index type 'HNSW'" not in str(error):
                raise
            self._ensure_vss_loaded()
            self._connection.executemany(upsert_sql, payload)

    def _ensure_vss_loaded(self) -> None:
        """Install/load vss extension for connections touching HNSW-indexed tables."""

        try:
            self._connection.execute("LOAD vss")
        except duckdb.Error:
            self._connection.execute("INSTALL vss")
            self._connection.execute("LOAD vss")


def _to_fixed_vector(vector: Sequence[float], dimensions: int) -> list[float]:
    values = [float(value) for value in vector[:dimensions]]
    if len(values) < dimensions:
        values.extend([0.0] * (dimensions - len(values)))
    return values
