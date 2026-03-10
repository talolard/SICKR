"""Build precomputed cosine-similarity neighbors from embedding snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt

_MIN_ROWS_FOR_NEIGHBORS = 2


@dataclass(frozen=True, slots=True)
class EmbeddingRow:
    """One persisted product embedding row."""

    product_key: str
    vector: tuple[float, ...]


def build_neighbor_rows(
    *,
    embedding_rows: Sequence[tuple[str, str, tuple[float, ...]]],
    neighbor_limit: int,
) -> dict[str, list[tuple[str, str, int, float]]]:
    """Return batch rows keyed by embedding model for neighbor-table inserts.

    The output rows follow:
    `(source_product_key, neighbor_product_key, neighbor_rank, cosine_similarity)`
    and contain up to `neighbor_limit` nearest neighbors per source product.
    """

    grouped = _group_rows_by_model(embedding_rows)
    output: dict[str, list[tuple[str, str, int, float]]] = {}
    for embedding_model, rows in grouped.items():
        output[embedding_model] = _build_model_neighbor_rows(
            rows=rows,
            neighbor_limit=neighbor_limit,
        )
    return output


def _group_rows_by_model(
    embedding_rows: Sequence[tuple[str, str, tuple[float, ...]]],
) -> dict[str, list[EmbeddingRow]]:
    grouped: dict[str, list[EmbeddingRow]] = {}
    for product_key, embedding_model, vector in embedding_rows:
        if not vector:
            continue
        grouped.setdefault(embedding_model, []).append(
            EmbeddingRow(product_key=product_key, vector=vector)
        )
    return grouped


def _build_model_neighbor_rows(
    *,
    rows: list[EmbeddingRow],
    neighbor_limit: int,
) -> list[tuple[str, str, int, float]]:
    if len(rows) < _MIN_ROWS_FOR_NEIGHBORS:
        return []

    normalized_rows = [_normalize_row(row) for row in rows]
    output_rows: list[tuple[str, str, int, float]] = []
    for source in normalized_rows:
        scored_neighbors: list[tuple[str, float]] = []
        for candidate in normalized_rows:
            if source.product_key == candidate.product_key:
                continue
            scored_neighbors.append(
                (
                    candidate.product_key,
                    _cosine_similarity_normalized(
                        source.normalized_vector, candidate.normalized_vector
                    ),
                )
            )
        scored_neighbors.sort(key=lambda item: (-item[1], item[0]))
        effective_limit = (
            len(scored_neighbors)
            if neighbor_limit <= 0
            else min(neighbor_limit, len(scored_neighbors))
        )
        for rank, (neighbor_key, similarity) in enumerate(
            scored_neighbors[:effective_limit], start=1
        ):
            output_rows.append((source.product_key, neighbor_key, rank, similarity))
    return output_rows


@dataclass(frozen=True, slots=True)
class _NormalizedEmbeddingRow:
    product_key: str
    normalized_vector: tuple[float, ...]


def _normalize_row(row: EmbeddingRow) -> _NormalizedEmbeddingRow:
    norm = sqrt(sum(value * value for value in row.vector))
    if norm <= 0.0:
        return _NormalizedEmbeddingRow(
            product_key=row.product_key,
            normalized_vector=tuple(0.0 for _ in row.vector),
        )
    return _NormalizedEmbeddingRow(
        product_key=row.product_key,
        normalized_vector=tuple(value / norm for value in row.vector),
    )


def _cosine_similarity_normalized(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    length = min(len(a), len(b))
    if length == 0:
        return 0.0
    return float(sum(a[idx] * b[idx] for idx in range(length)))
