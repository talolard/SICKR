from __future__ import annotations

from ingest.precompute_embedding_neighbors import build_neighbor_rows


def test_build_neighbor_rows_returns_ranked_neighbors_per_source() -> None:
    rows = [
        ("A", "gemini-embedding-001", (1.0, 0.0)),
        ("B", "gemini-embedding-001", (0.8, 0.2)),
        ("C", "gemini-embedding-001", (0.0, 1.0)),
    ]

    neighbor_rows = build_neighbor_rows(embedding_rows=rows, neighbor_limit=2)

    model_rows = neighbor_rows["gemini-embedding-001"]
    source_a_rows = [row for row in model_rows if row[0] == "A"]
    assert source_a_rows[0][1] == "B"
    assert source_a_rows[0][2] == 1
    assert source_a_rows[1][1] == "C"
    assert source_a_rows[1][2] == 2
