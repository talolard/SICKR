from __future__ import annotations

import duckdb
import pytest

from tal_maria_ikea.ingest.repository import IndexRepository


def test_read_embedding_inputs_from_known_view() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA app")
    connection.execute(
        "CREATE VIEW app.embedding_input_v1_baseline AS "
        "SELECT '1-DE' AS canonical_product_key, 't1' AS embedding_text"
    )
    connection.execute(
        "CREATE VIEW app.embedding_input_v2_metadata_first AS "
        "SELECT '2-DE' AS canonical_product_key, 't2' AS embedding_text"
    )

    repository = IndexRepository(connection)
    rows = repository.read_embedding_inputs("app.embedding_input_v1_baseline", subset_limit=None)

    assert rows == [("1-DE", "t1")]


def test_read_embedding_inputs_rejects_unknown_view() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA app")
    connection.execute(
        "CREATE VIEW app.embedding_input_v1_baseline AS "
        "SELECT '1-DE' AS canonical_product_key, 't1' AS embedding_text"
    )
    connection.execute(
        "CREATE VIEW app.embedding_input_v2_metadata_first AS "
        "SELECT '2-DE' AS canonical_product_key, 't2' AS embedding_text"
    )

    repository = IndexRepository(connection)

    with pytest.raises(ValueError, match="Unsupported embedding input view"):
        repository.read_embedding_inputs("app.unsupported", subset_limit=None)


def test_embedding_vector_dimensions_reads_fixed_array_size() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA app")
    connection.execute(
        """
        CREATE TABLE app.product_embeddings (
            canonical_product_key VARCHAR,
            embedding_model VARCHAR,
            strategy_version VARCHAR,
            run_id VARCHAR,
            embedding_vector FLOAT[256],
            embedded_text VARCHAR,
            embedded_at TIMESTAMP
        )
        """
    )

    repository = IndexRepository(connection)
    assert repository.embedding_vector_dimensions() == 256
