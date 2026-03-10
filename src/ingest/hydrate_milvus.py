"""Hydrate Milvus Lite collection from DuckDB embedding snapshots."""

from __future__ import annotations

from ikea_agent.config import get_settings
from ikea_agent.retrieval.catalog_repository import EmbeddingSnapshotRepository
from ikea_agent.retrieval.service import MilvusAccessService
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
from ingest.precompute_embedding_neighbors import build_neighbor_rows


def main() -> None:
    """Load embedding rows into Milvus and precompute similarity neighbors."""

    settings = get_settings()
    engine = create_duckdb_engine(settings.duckdb_path)
    ensure_runtime_schema(engine)

    repository = EmbeddingSnapshotRepository(engine)
    rows = repository.read_embedding_rows(embedding_model=settings.gemini_model)

    milvus_service = MilvusAccessService(settings)
    milvus_service.upsert_rows(rows)

    neighbor_rows_by_model = build_neighbor_rows(
        embedding_rows=rows,
        neighbor_limit=settings.embedding_neighbor_limit,
    )
    total_inserted = 0
    for embedding_model, neighbor_rows in neighbor_rows_by_model.items():
        inserted = repository.replace_neighbor_rows(
            embedding_model=embedding_model,
            rows=neighbor_rows,
        )
        total_inserted += inserted
    print(
        f"Hydrated {len(rows)} embeddings to Milvus and {total_inserted} precomputed "
        "embedding-neighbor rows to DuckDB."
    )


if __name__ == "__main__":
    main()
