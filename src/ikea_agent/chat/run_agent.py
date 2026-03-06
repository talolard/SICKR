"""CLI utility to run the chat agent directly from a terminal session.

This runner is intended for fast local validation of prompt/tool behavior
without starting the web server. It builds the same runtime dependencies and
agent definition used by the FastAPI app, then executes one user prompt.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from ikea_agent.chat.agent import build_chat_agent
from ikea_agent.chat.deps import ChatAgentDeps, ChatAgentState
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.config import AppSettings, get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore

DEFAULT_PROMPT = "I have a 7x2 meter hallway with no natural light and two doors one on each end"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the IKEA chat agent once from CLI.")
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="User prompt to send to the agent for a single run.",
    )
    parser.add_argument(
        "--session-id",
        default=f"cli-run-{uuid4().hex[:12]}",
        help="Session id attached to agent state and telemetry.",
    )
    parser.add_argument(
        "--duckdb-path",
        default=None,
        help=(
            "Optional DuckDB path override. Useful when the default DB is locked by "
            "another running process."
        ),
    )
    parser.add_argument(
        "--milvus-lite-uri",
        default=None,
        help=(
            "Optional Milvus Lite URI override. Defaults to an isolated temp file to avoid "
            "lock conflicts with running services."
        ),
    )
    return parser


def _build_runtime_with_fallback(settings: AppSettings) -> ChatRuntime:
    """Build runtime and fall back to a temp DuckDB copy when default DB is locked."""

    try:
        return build_chat_runtime()
    except Exception as exc:  # pragma: no cover - exercised in local lock scenarios
        message = str(exc)
        if "Could not set lock on file" not in message:
            raise
        source = Path(settings.duckdb_path)
        fallback = Path(gettempdir()) / "ikea_agent" / f"duckdb_cli_{uuid4().hex[:8]}.duckdb"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, fallback)
        else:
            fallback.touch()
        print(f"DuckDB locked at {source}; retrying with isolated copy: {fallback}")
        os.environ["DUCKDB_PATH"] = str(fallback)
        get_settings.cache_clear()
        return build_chat_runtime()


async def _run_once(
    *,
    prompt: str,
    session_id: str,
    duckdb_path: str | None,
    milvus_lite_uri: str | None,
) -> str:
    if duckdb_path:
        os.environ["DUCKDB_PATH"] = duckdb_path
    if milvus_lite_uri:
        os.environ["MILVUS_LITE_URI"] = milvus_lite_uri
    else:
        isolated_milvus_uri = Path(gettempdir()) / "ikea_agent" / f"milvus_cli_{uuid4().hex[:8]}.db"
        isolated_milvus_uri.parent.mkdir(parents=True, exist_ok=True)
        os.environ["MILVUS_LITE_URI"] = str(isolated_milvus_uri)
    if duckdb_path or milvus_lite_uri:
        get_settings.cache_clear()
    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)

    runtime = _build_runtime_with_fallback(settings)
    attachment_store = AttachmentStore(Path(settings.artifact_root_dir))
    deps = ChatAgentDeps(
        runtime=runtime,
        attachment_store=attachment_store,
        floor_plan_scene_store=FloorPlanSceneStore(),
        state=ChatAgentState(session_id=session_id),
    )
    agent = build_chat_agent()
    result = await agent.run(prompt, deps=deps)
    return result.output


def main() -> None:
    """Execute one direct agent run and print final assistant output."""

    args = _build_parser().parse_args()
    output = asyncio.run(
        _run_once(
            prompt=args.prompt,
            session_id=args.session_id,
            duckdb_path=args.duckdb_path,
            milvus_lite_uri=args.milvus_lite_uri,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
