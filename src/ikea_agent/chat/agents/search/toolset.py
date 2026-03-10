"""Local toolset for search agent."""

from __future__ import annotations

from logging import getLogger

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.shared import (
    build_room_3d_snapshot_context_payload,
    room_3d_repository,
    search_repository,
    telemetry_context,
)
from ikea_agent.chat.search_pipeline import run_search_pipeline
from ikea_agent.persistence.room_3d_repository import Room3DSnapshotEntry
from ikea_agent.shared.types import RetrievalFilters, SearchGraphToolResult

logger = getLogger(__name__)

TOOL_NAMES: tuple[str, ...] = (
    "run_search_graph",
    "list_room_3d_snapshot_context",
)


async def run_search_graph(
    ctx: RunContext[SearchAgentDeps],
    semantic_query: str,
    limit: int = 20,
    candidate_pool_limit: int | None = None,
    filters: RetrievalFilters | None = None,
) -> SearchGraphToolResult:
    """Run semantic search, apply rerank + MMR diversification, and return results."""

    target_pool_limit = candidate_pool_limit
    if target_pool_limit is not None:
        target_pool_limit = max(limit, min(500, target_pool_limit))
    output = await run_search_pipeline(
        runtime=ctx.deps.runtime,
        semantic_query=semantic_query,
        limit=limit,
        candidate_pool_limit=target_pool_limit,
        filters=filters,
    )
    logger.info(
        "search_query_completed",
        extra={
            "query_text": semantic_query,
            "result_count": output.total_candidates,
            "returned_result_count": len(output.results),
            "dominance_warning": output.warning.dominant_family if output.warning else None,
            **telemetry_context(ctx.deps.state),
        },
    )
    search_repo = search_repository(ctx.deps.runtime)
    if search_repo is not None:
        search_repo.record_search_run(
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            query_text=semantic_query,
            filters=filters,
            warning=output.warning,
            total_candidates=output.total_candidates,
            results=output.results,
        )
    return output


def list_room_3d_snapshot_context(ctx: RunContext[SearchAgentDeps]) -> dict[str, object]:
    """Return captured 3D snapshot context from state and persisted thread records."""

    persisted: list[Room3DSnapshotEntry] = []
    repository = room_3d_repository(ctx.deps.runtime)
    if repository is not None and ctx.deps.state.thread_id is not None:
        persisted = repository.list_room_3d_snapshots(thread_id=ctx.deps.state.thread_id)
    payload = build_room_3d_snapshot_context_payload(
        state_snapshots=ctx.deps.state.room_3d_snapshots,
        persisted_snapshots=persisted,
    )
    logger.info(
        "list_room_3d_snapshot_context",
        extra={
            "state_snapshot_count": payload["state_count"],
            "persisted_snapshot_count": payload["persisted_count"],
            **telemetry_context(ctx.deps.state),
        },
    )
    return payload


def build_search_toolset() -> FunctionToolset[SearchAgentDeps]:
    """Build toolset for search agent."""

    return FunctionToolset(
        tools=[
            Tool(run_search_graph, name="run_search_graph"),
            Tool(list_room_3d_snapshot_context, name="list_room_3d_snapshot_context"),
        ]
    )
