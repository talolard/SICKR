"""CLI utility to run one named first-class agent from a terminal session."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from ikea_agent.chat.agents.floor_plan_intake.deps import FloorPlanIntakeDeps
from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.index import build_agent_ag_ui_agent
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.state import (
    FloorPlanIntakeAgentState,
    ImageAnalysisAgentState,
    SearchAgentState,
)
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.shared.sqlalchemy_db import build_duckdb_sqlalchemy_url
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore

DEFAULT_PROMPT = "I have a 7x2 meter hallway with no natural light and two doors one on each end"
DEFAULT_AGENT = "floor_plan_intake"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one IKEA agent once from CLI.")
    parser.add_argument(
        "--agent",
        default=DEFAULT_AGENT,
        choices=["floor_plan_intake", "search", "image_analysis"],
        help="Named agent to execute.",
    )
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
        "--database-url",
        default=None,
        help="Optional DATABASE_URL override for one CLI run.",
    )
    parser.add_argument(
        "--milvus-uri",
        default=None,
        help="Optional shared Milvus URI override for one CLI run.",
    )
    parser.add_argument(
        "--duckdb-path",
        default=None,
        help="Legacy compatibility alias that maps to a DuckDB-backed DATABASE_URL.",
    )
    return parser


def _build_deps(
    *,
    agent_name: str,
    runtime: ChatRuntime,
    attachment_store: AttachmentStore,
    session_id: str,
) -> FloorPlanIntakeDeps | SearchAgentDeps | ImageAnalysisAgentDeps:
    if agent_name == "floor_plan_intake":
        return FloorPlanIntakeDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            floor_plan_scene_store=FloorPlanSceneStore(),
            state=FloorPlanIntakeAgentState(session_id=session_id),
        )
    if agent_name == "search":
        return SearchAgentDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            state=SearchAgentState(session_id=session_id),
        )
    if agent_name == "image_analysis":
        return ImageAnalysisAgentDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            state=ImageAnalysisAgentState(session_id=session_id),
        )
    msg = f"Unsupported agent `{agent_name}`"
    raise ValueError(msg)


async def _run_once(
    *,
    agent_name: str,
    prompt: str,
    session_id: str,
    database_url: str | None,
    milvus_uri: str | None,
    duckdb_path: str | None,
) -> str:
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    if milvus_uri:
        os.environ["MILVUS_URI"] = milvus_uri
    if duckdb_path:
        os.environ["DATABASE_URL"] = build_duckdb_sqlalchemy_url(duckdb_path)
    if database_url or milvus_uri or duckdb_path:
        get_settings.cache_clear()
    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)

    runtime = build_chat_runtime()
    attachment_store = AttachmentStore(Path(settings.artifact_root_dir))
    deps = _build_deps(
        agent_name=agent_name,
        runtime=runtime,
        attachment_store=attachment_store,
        session_id=session_id,
    )
    agent = build_agent_ag_ui_agent(agent_name)
    result = await agent.run(prompt, deps=deps)
    return result.output


def main() -> None:
    """Execute one direct agent run and print the final assistant output."""

    args = _build_parser().parse_args()
    output = asyncio.run(
        _run_once(
            agent_name=args.agent,
            prompt=args.prompt,
            session_id=args.session_id,
            database_url=args.database_url,
            milvus_uri=args.milvus_uri,
            duckdb_path=args.duckdb_path,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
