from __future__ import annotations

from ikea_agent.eval.metrics import (
    aggregate_metrics,
    compute_hit_at_k,
    compute_mrr,
    compute_recall_at_k,
)


def test_compute_hit_at_k() -> None:
    expected = {"a", "b"}
    predicted = ["z", "b", "x"]

    assert compute_hit_at_k(expected, predicted, 2) == 1.0


def test_compute_recall_at_k() -> None:
    expected = {"a", "b", "c"}
    predicted = ["c", "x", "b"]

    assert compute_recall_at_k(expected, predicted, 2) == 1.0 / 3.0


def test_compute_mrr() -> None:
    expected = {"p2"}
    predicted = ["p1", "p2", "p3"]

    assert compute_mrr(expected, predicted) == 0.5


def test_aggregate_metrics() -> None:
    metrics = aggregate_metrics([(1.0, 0.5, 1.0), (0.0, 0.0, 0.0)])

    assert metrics.hit_at_k == 0.5
    assert metrics.recall_at_k == 0.25
    assert metrics.mrr == 0.5
    assert metrics.total_queries == 2
