from __future__ import annotations

from pathlib import Path

from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.retrieval.catalog_repository import CatalogRepository, EmbeddingSnapshotRepository
from ikea_agent.shared.bootstrap import ensure_runtime_schema


def test_replace_and_read_neighbor_similarities(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "embedding_neighbors.sqlite")
    ensure_runtime_schema(engine)

    snapshot_repository = EmbeddingSnapshotRepository(engine)
    inserted = snapshot_repository.replace_neighbor_rows(
        embedding_model="gemini-embedding-001",
        rows=[
            ("A", "B", 1, 0.92),
            ("A", "C", 2, 0.55),
            ("B", "A", 1, 0.92),
            ("B", "C", 2, 0.11),
        ],
    )

    assert inserted == 4

    catalog_repository = CatalogRepository(engine)
    lookup = catalog_repository.read_neighbor_similarities(
        embedding_model="gemini-embedding-001",
        product_keys=["A", "B", "C"],
    )

    assert lookup[("A", "B")] == 0.92
    assert lookup[("B", "A")] == 0.92
    assert lookup[("A", "C")] == 0.55
