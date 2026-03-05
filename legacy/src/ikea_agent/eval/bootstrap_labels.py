"""Bootstrap eval labels from current retrieval results for generated queries."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from ikea_agent.eval.repository import EvalRepository

from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging, get_logger
from ikea_agent.retrieval.service import RetrievalService
from ikea_agent.shared.db import connect_db, run_sql_file
from ikea_agent.shared.types import RetrievalRequest


@dataclass(frozen=True, slots=True)
class BootstrapLabelOptions:
    """CLI options for automatic eval label bootstrap."""

    subset_id: str | None
    prompt_version: str | None
    top_k: int


def run_bootstrap_labels(options: BootstrapLabelOptions) -> int:
    """Create eval labels from current retrieval top-k for generated queries."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("eval.bootstrap_labels")

    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/41_eval_registry.sql")
    repository = EvalRepository(connection)
    retrieval_service = RetrievalService()

    generated_queries = repository.list_generated_queries(
        subset_id=options.subset_id,
        prompt_version=options.prompt_version,
    )
    if not generated_queries:
        message = "No generated queries available for bootstrap labeling."
        raise RuntimeError(message)

    logger.info(
        "eval_bootstrap_labels_start",
        query_count=len(generated_queries),
        top_k=options.top_k,
        subset_id=options.subset_id,
        prompt_version=options.prompt_version,
    )

    labels: list[tuple[str, str, int]] = []
    for index, (eval_query_id, query_text) in enumerate(generated_queries, start=1):
        request = RetrievalRequest(query_text=query_text, result_limit=options.top_k)
        results = retrieval_service.retrieve(request, source="eval_bootstrap")
        for rank, result in enumerate(results[: options.top_k], start=1):
            labels.append((eval_query_id, result.canonical_product_key, rank))
        if index % 25 == 0:
            logger.info(
                "eval_bootstrap_labels_progress",
                processed_queries=index,
                total_queries=len(generated_queries),
                labels_buffered=len(labels),
            )

    repository.upsert_eval_labels(labels)
    logger.info(
        "eval_bootstrap_labels_complete",
        query_count=len(generated_queries),
        label_count=len(labels),
    )
    print(
        json.dumps(
            {"labeled_queries": len(generated_queries), "label_count": len(labels)}, indent=2
        )
    )
    return len(generated_queries)


def _parse_args() -> BootstrapLabelOptions:
    parser = argparse.ArgumentParser(description="Bootstrap eval labels from retrieval top-k.")
    parser.add_argument("--subset-id", default=None)
    parser.add_argument("--prompt-version", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")
    return BootstrapLabelOptions(
        subset_id=args.subset_id,
        prompt_version=args.prompt_version,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    run_bootstrap_labels(_parse_args())
