"""Search and session-context tool registrations for the chat agent."""

from __future__ import annotations

from logging import getLogger

from pydantic_ai import Agent, RunContext

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from ikea_agent.chat.tools.support import (
    build_room_3d_snapshot_context_payload,
    room_3d_repository,
    search_repository,
    telemetry_context,
)
from ikea_agent.persistence.room_3d_repository import Room3DSnapshotEntry
from ikea_agent.shared.types import AttachmentRef, RetrievalFilters, SearchGraphToolResult

logger = getLogger(__name__)


def register_search_context_tools(agent: Agent[ChatAgentDeps, str]) -> None:
    """Register search and shared-state context tools on the chat agent."""

    @agent.tool
    async def run_search_graph(
        ctx: RunContext[ChatAgentDeps],
        semantic_query: str,
        limit: int = 20,
        candidate_pool_limit: int | None = None,
        filters: RetrievalFilters | None = None,
    ) -> SearchGraphToolResult:
        """Run semantic search, apply rerank + MMR diversification, and return results."""

        target_pool_limit = candidate_pool_limit
        if target_pool_limit is not None:
            target_pool_limit = max(limit, min(500, target_pool_limit))
        graph = build_chat_graph()
        result = await graph.run(
            ParseUserIntentNode(
                user_message=semantic_query,
                result_limit=limit,
                candidate_pool_limit=target_pool_limit,
            ),
            state=ChatGraphState(filters=filters),
            deps=ChatGraphDeps(runtime=ctx.deps.runtime),
        )
        logger.info(
            "graph_query_completed",
            extra={
                "query_text": semantic_query,
                "result_count": result.output.total_candidates,
                "returned_result_count": len(result.output.product_matches),
                "dominance_warning": (
                    result.output.warning.dominant_family if result.output.warning else None
                ),
                **telemetry_context(ctx),
            },
        )
        output = SearchGraphToolResult(
            results=result.output.product_matches,
            warning=result.output.warning,
            total_candidates=result.output.total_candidates,
            returned_count=len(result.output.product_matches),
        )
        search_repo = search_repository(ctx)
        if search_repo is not None:
            search_repo.record_search_run(
                thread_id=ctx.deps.state.thread_id or "anonymous-thread",
                run_id=ctx.deps.state.run_id,
                query_text=semantic_query,
                filters=filters,
                warning=result.output.warning,
                total_candidates=result.output.total_candidates,
                results=result.output.product_matches,
            )
        return output

    @agent.tool
    async def list_uploaded_images(ctx: RunContext[ChatAgentDeps]) -> list[AttachmentRef]:
        """List uploaded images from AG-UI shared state."""

        logger.info(
            "list_uploaded_images",
            extra={
                "attachment_count": len(ctx.deps.state.attachments),
                **telemetry_context(ctx),
            },
        )
        return ctx.deps.state.attachments

    @agent.tool
    def list_room_3d_snapshot_context(ctx: RunContext[ChatAgentDeps]) -> dict[str, object]:
        """Return captured 3D snapshot context from state and persisted thread records."""

        persisted: list[Room3DSnapshotEntry] = []
        repository = room_3d_repository(ctx)
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
                **telemetry_context(ctx),
            },
        )
        return payload
