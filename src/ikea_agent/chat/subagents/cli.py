"""Shared CLI for executing any registered chat subagent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from ikea_agent.chat.subagents.registry import get_subagent


def build_parser() -> argparse.ArgumentParser:
    """Construct the shared subagent CLI argument parser."""

    parser = argparse.ArgumentParser(description="Run one registered chat subagent.")
    parser.add_argument("--agent", required=True, help="Registered subagent name")
    parser.add_argument("--input", default=None, help="Inline input payload (JSON or plain text)")
    parser.add_argument(
        "--input-file",
        default=None,
        help="Path to file containing input payload (JSON or plain text)",
    )
    return parser


def _read_input_payload(input_value: str | None, input_file: str | None) -> str:
    """Read payload from inline value or file and enforce one source of truth."""

    if input_value and input_file:
        msg = "Provide only one of --input or --input-file."
        raise ValueError(msg)
    if input_file:
        return Path(input_file).read_text(encoding="utf-8")
    if input_value is not None:
        return input_value
    return ""


def main(argv: list[str] | None = None) -> int:
    """Execute one registered subagent and print JSON output."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        registration = get_subagent(args.agent)
        raw_input = _read_input_payload(args.input, args.input_file)
        output = asyncio.run(_run_subagent(registration.run, raw_input))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "agent": registration.name, "output": output}, ensure_ascii=True))
    return 0


async def _run_subagent(
    run: Callable[[str], Awaitable[dict[str, object]]],
    raw_input: str,
) -> dict[str, object]:
    """Await one subagent runner and satisfy strict coroutine typing."""

    return await run(raw_input)


if __name__ == "__main__":
    raise SystemExit(main())
