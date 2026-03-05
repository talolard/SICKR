"""Hydrate Milvus Lite collection from DuckDB embedding snapshots."""

from __future__ import annotations

from ikea_agent.config import get_settings
from ikea_agent.retrieval.catalog_repository import EmbeddingSnapshotRepository
from ikea_agent.retrieval.service import MilvusAccessService
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db import connect_db


def main() -> None:
    """Load embedding rows from DuckDB and upsert them into Milvus Lite."""

    settings = get_settings()
    connection = connect_db(settings.duckdb_path)
    ensure_runtime_schema(connection)

    repository = EmbeddingSnapshotRepository(connection)
    rows = repository.read_embedding_rows(embedding_model=settings.gemini_model)

    milvus_service = MilvusAccessService(settings)
    milvus_service.upsert_rows(rows)


if __name__ == "__main__":
    main()
