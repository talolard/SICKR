"""Run retrieval evaluation against labeled query sets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.eval.metrics import (
    aggregate_metrics,
    compute_hit_at_k,
    compute_mrr,
    compute_recall_at_k,
)
from tal_maria_ikea.eval.repository import EvalRepository
from tal_maria_ikea.logging_config import configure_logging, get_logger
from tal_maria_ikea.retrieval.service import RetrievalService
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import RetrievalRequest


@dataclass(frozen=True, slots=True)
class EvalRunOptions:
    """CLI options for evaluation execution."""

    index_run_id: str
    k: int


def run_eval(options: EvalRunOptions) -> dict[str, float | int | str]:
    """Execute retrieval over labeled queries and persist metrics."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("eval.run")

    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/41_eval_registry.sql")

    repository = EvalRepository(connection)
    retrieval_service = RetrievalService()

    generated_count = repository.count_generated_queries()
    if generated_count == 0:
        message = (
            "No eval queries found. Run `uv run python -m tal_maria_ikea.eval.generate "
            "--subset-id <id> --prompt-version <version> --target-count 200` first."
        )
        raise RuntimeError(message)

    labeled_count = repository.count_labeled_queries()
    if labeled_count == 0:
        message = (
            "No eval labels found. Add expected canonical keys to app.eval_labels "
            "before running evaluation."
        )
        raise RuntimeError(message)

    metrics_rows: list[tuple[float, float, float]] = []
    labeled_queries = repository.get_labeled_queries()

    for _, query_text, expected_keys in labeled_queries:
        request = RetrievalRequest(query_text=query_text, result_limit=options.k)
        results = retrieval_service.retrieve(request, source="eval")
        predicted_keys = [item.canonical_product_key for item in results]
        expected_set = set(expected_keys)

        hit = compute_hit_at_k(expected_set, predicted_keys, options.k)
        recall = compute_recall_at_k(expected_set, predicted_keys, options.k)
        mrr = compute_mrr(expected_set, predicted_keys)
        metrics_rows.append((hit, recall, mrr))

    metrics = aggregate_metrics(metrics_rows)

    eval_run_id = f"eval-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    repository.insert_eval_run(
        eval_run_id=eval_run_id,
        index_run_id=options.index_run_id,
        strategy_version="v2_metadata_first",
        embedding_model=settings.gemini_model,
        k=options.k,
        hit_at_k=metrics.hit_at_k,
        recall_at_k=metrics.recall_at_k,
        mrr=metrics.mrr or 0.0,
    )

    report = {
        "eval_run_id": eval_run_id,
        "query_count": metrics.total_queries,
        "hit_at_k": metrics.hit_at_k,
        "recall_at_k": metrics.recall_at_k,
        "mrr": metrics.mrr or 0.0,
    }

    logger.info("eval_run_complete", **report)
    print(json.dumps(report, indent=2))
    return report


def _parse_args() -> EvalRunOptions:
    parser = argparse.ArgumentParser(description="Run retrieval evaluation using labeled queries.")
    parser.add_argument("--index-run-id", required=True)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    return EvalRunOptions(index_run_id=args.index_run_id, k=args.k)


if __name__ == "__main__":
    run_eval(_parse_args())
