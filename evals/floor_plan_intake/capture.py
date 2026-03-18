"""Capture live floor-plan intake runs for fixture authoring and review."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import NoReturn

import anyio
from pydantic_ai.models import override_allow_model_requests

from evals.floor_plan_intake import (
    FloorPlanIntakeEvalHarness,
    build_floor_plan_intake_eval_dataset,
)
from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture live floor-plan intake eval runs.")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_names",
        help="Restrict capture to one or more named eval cases.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/floor-plan-intake-eval-captures"),
        help="Directory where per-case capture JSON files should be written.",
    )
    return parser


def _missing_api_key() -> bool:
    settings = get_settings()
    return not bool(settings.gemini_api_key)


def _exit_missing_key() -> NoReturn:
    raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY before capturing eval runs.")


async def _run_capture(*, case_names: set[str] | None, output_dir: Path) -> None:
    dataset = build_floor_plan_intake_eval_dataset()
    harness = FloorPlanIntakeEvalHarness()
    async_output_dir = anyio.Path(output_dir)
    await async_output_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, object]] = []

    with override_allow_model_requests(True):
        for case in dataset.cases:
            if case_names is not None and case.name not in case_names:
                continue
            capture = await harness.capture_case(case.inputs)
            output_path = output_dir / f"{case.name}.json"
            payload = {
                "case_name": case.name,
                "inputs": asdict(case.inputs),
                "capture": capture.to_payload(),
            }
            async_output_path = anyio.Path(output_path)
            await async_output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            index.append(
                {
                    "case_name": case.name,
                    "source_trace_id": case.inputs.source_trace_id,
                    "output_path": str(output_path),
                }
            )

    index_path = anyio.Path(output_dir / "index.json")
    await index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")


def main() -> None:
    """Run the capture CLI."""

    args = _build_parser().parse_args()
    os.environ.setdefault("ALLOW_MODEL_REQUESTS", "1")
    get_settings.cache_clear()
    if _missing_api_key():
        _exit_missing_key()
    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    case_names = set(args.case_names) if args.case_names else None
    asyncio.run(_run_capture(case_names=case_names, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
