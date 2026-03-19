from __future__ import annotations

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.retrieval.schema import product_embeddings
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db_contract import (
    PRODUCT_EMBEDDING_DIMENSIONS,
    PRODUCT_EMBEDDING_VECTOR_INDEX_NAME,
    PRODUCT_EMBEDDING_VECTOR_OPCLASS,
)


def test_embedding_vector_compiles_to_pgvector_for_postgres() -> None:
    compiled = product_embeddings.c.embedding_vector.type.compile(dialect=postgresql.dialect())

    assert compiled == f"HALFVEC({PRODUCT_EMBEDDING_DIMENSIONS})"


def test_embedding_vector_index_uses_hnsw_cosine_in_postgres() -> None:
    index = next(
        candidate
        for candidate in product_embeddings.indexes
        if candidate.name == PRODUCT_EMBEDDING_VECTOR_INDEX_NAME
    )

    compiled = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert "USING hnsw" in compiled
    assert PRODUCT_EMBEDDING_VECTOR_OPCLASS in compiled


def test_embedding_vector_uses_json_for_sqlite_fallback(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "embedding_schema.sqlite")
    ensure_runtime_schema(engine)

    with engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "PRAGMA catalog.table_info(product_embeddings)"
        ).fetchall()

    embedding_vector_row = next(row for row in rows if row[1] == "embedding_vector")
    assert embedding_vector_row[2] == "JSON"
