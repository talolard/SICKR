"""Metric computations for retrieval evaluation."""

from __future__ import annotations

from ikea_agent.shared.types import EvalRunMetrics


def compute_hit_at_k(expected_keys: set[str], predicted_keys: list[str], k: int) -> float:
    """Return hit@k for one query."""

    top = set(predicted_keys[:k])
    return 1.0 if expected_keys & top else 0.0


def compute_recall_at_k(expected_keys: set[str], predicted_keys: list[str], k: int) -> float:
    """Return recall@k for one query."""

    if not expected_keys:
        return 0.0
    top = set(predicted_keys[:k])
    return len(expected_keys & top) / len(expected_keys)


def compute_mrr(expected_keys: set[str], predicted_keys: list[str]) -> float:
    """Return reciprocal rank of the first expected key."""

    for index, key in enumerate(predicted_keys, start=1):
        if key in expected_keys:
            return 1.0 / index
    return 0.0


def aggregate_metrics(rows: list[tuple[float, float, float]]) -> EvalRunMetrics:
    """Aggregate per-query metrics into one report object."""

    if not rows:
        return EvalRunMetrics(hit_at_k=0.0, recall_at_k=0.0, mrr=0.0, total_queries=0)

    count = len(rows)
    hit = sum(row[0] for row in rows) / count
    recall = sum(row[1] for row in rows) / count
    mrr = sum(row[2] for row in rows) / count
    return EvalRunMetrics(hit_at_k=hit, recall_at_k=recall, mrr=mrr, total_queries=count)
