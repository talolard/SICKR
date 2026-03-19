from __future__ import annotations

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from ikea_agent.retrieval.schema import product_embeddings
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db_contract import (
    PRODUCT_EMBEDDING_DIMENSIONS,
    PRODUCT_EMBEDDING_VECTOR_INDEX_NAME,
    PRODUCT_EMBEDDING_VECTOR_OPCLASS,
)
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine


def test_embedding_vector_compiles_to_pgvector_for_postgres() -> None:
    compiled = product_embeddings.c.embedding_vector.type.compile(dialect=postgresql.dialect())

    assert compiled == f"VECTOR({PRODUCT_EMBEDDING_DIMENSIONS})"


def test_embedding_vector_index_uses_hnsw_cosine_in_postgres() -> None:
    index = next(
        candidate
        for candidate in product_embeddings.indexes
        if candidate.name == PRODUCT_EMBEDDING_VECTOR_INDEX_NAME
    )

    compiled = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert "USING hnsw" in compiled
    assert PRODUCT_EMBEDDING_VECTOR_OPCLASS in compiled


def test_embedding_vector_falls_back_to_array_for_duckdb(tmp_path: Path) -> None:
    engine = create_duckdb_engine(str(tmp_path / "embedding_schema.duckdb"))
    ensure_runtime_schema(engine)

    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'catalog'
              AND table_name = 'product_embeddings'
              AND column_name = 'embedding_vector'
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "FLOAT[]"
