"""CLI entrypoint for live floor-plan intake evals.

The canonical command is `uv run python -m evals.floor_plan_intake`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import NoReturn

from pydantic_ai.models import override_allow_model_requests

from evals.base import assert_report_has_no_failures
from evals.floor_plan_intake import (
    FloorPlanIntakeEvalHarness,
    build_floor_plan_intake_eval_dataset,
)
from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live floor-plan intake evals.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-case inputs, outputs, and evaluator reasons.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Maximum number of eval cases to run concurrently.",
    )
    return parser


def _missing_api_key() -> bool:
    settings = get_settings()
    return not bool(settings.gemini_api_key)


def _exit_missing_key() -> NoReturn:
    raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY before running evals.")


async def _run(verbose: bool, max_concurrency: int) -> None:
    dataset = build_floor_plan_intake_eval_dataset()
    harness = FloorPlanIntakeEvalHarness()
    with override_allow_model_requests(True):
        report = await dataset.evaluate(
            harness.run_case,
            name=dataset.name,
            max_concurrency=max_concurrency,
        )
    report.print(
        include_input=verbose,
        include_output=verbose,
        include_reasons=True,
    )
    assert_report_has_no_failures(report)


def main() -> None:
    """Run the direct floor-plan intake eval harness."""

    args = _build_parser().parse_args()
    os.environ.setdefault("ALLOW_MODEL_REQUESTS", "1")
    get_settings.cache_clear()
    if _missing_api_key():
        _exit_missing_key()
    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    asyncio.run(_run(verbose=args.verbose, max_concurrency=args.max_concurrency))


if __name__ == "__main__":
    main()
