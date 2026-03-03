from __future__ import annotations

import duckdb

from tal_maria_ikea.ingest.repository import IndexRepository


def test_read_embedding_inputs_from_known_view() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA app")
    connection.execute(
        "CREATE VIEW app.embedding_input AS "
        "SELECT '1-DE' AS canonical_product_key, 't1' AS embedding_text"
    )

    repository = IndexRepository(connection)
    rows = repository.read_embedding_inputs(subset_limit=None)

    assert rows == [("1-DE", "t1")]


def test_embedding_vector_dimensions_reads_fixed_array_size() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA app")
    connection.execute(
        """
        CREATE TABLE app.product_embeddings (
            canonical_product_key VARCHAR,
            embedding_model VARCHAR,
            run_id VARCHAR,
            embedding_vector FLOAT[256],
            embedded_text VARCHAR,
            embedded_at TIMESTAMP
        )
        """
    )

    repository = IndexRepository(connection)
    assert repository.embedding_vector_dimensions() == 256
