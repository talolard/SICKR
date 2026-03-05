"""Typed chat graph for parse -> retrieve -> rerank orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.shared.types import (
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResult,
    ShortRetrievalResult,
)

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatGraphDeps:
    """Typed dependency container used by all graph nodes."""

    runtime: ChatRuntime


@dataclass(slots=True)
class ChatGraphState:
    """Mutable graph state shared between chat pipeline nodes."""

    filters: RetrievalFilters | None = None
    user_message: str = ""
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class ChatGraphResult:
    """Final typed payload returned by the chat graph."""

    request_id: str
    product_matches: list[ShortRetrievalResult]


@dataclass(frozen=True, slots=True)
class ParseUserIntentNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Initialize graph state for one incoming user chat message."""

    user_message: str

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Normalize and store the user message in graph state."""

        ctx.state.user_message = self.user_message.strip()
        return RetrieveCandidatesNode()


@dataclass(frozen=True, slots=True)
class RetrieveCandidatesNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Run semantic retrieval against product embeddings."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Execute typed retrieval and pass candidates to reranking."""

        request = RetrievalRequest(
            query_text=ctx.state.user_message,
            result_limit=max(200, ctx.deps.runtime.settings.default_query_limit),
            filters=ctx.state.filters or RetrievalFilters(),
        )
        execution = await ctx.deps.runtime.retrieval_service.retrieve_with_trace(
            request,
            source="chat",
        )
        ctx.state.request_id = execution.request_id
        return RerankNode(retrieval_results=execution.results)


@dataclass(frozen=True, slots=True)
class RerankNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Apply reranking backend to semantic retrieval candidates."""

    retrieval_results: list[RetrievalResult]

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Apply reranking and project results for agent tools."""

        reranked_items = ctx.deps.runtime.reranker_service.rerank(
            query_text=ctx.state.user_message,
            results=self.retrieval_results,
        )
        reranked_results = [item.result.to_short_result() for item in reranked_items]
        return ReturnAnswerNode(reranked_results=reranked_results)


@dataclass(frozen=True, slots=True)
class ReturnAnswerNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Return final graph payload to HTTP or agent callers."""

    reranked_results: list[ShortRetrievalResult]

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> End[ChatGraphResult]:
        """Finalize graph output payload."""

        logger.info("chat_answer_ready based on %d results", len(self.reranked_results))
        return End(
            ChatGraphResult(
                request_id=ctx.state.request_id,
                product_matches=self.reranked_results,
            )
        )


def build_chat_graph() -> Graph[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
    """Create chat graph instance with explicit node registry."""

    return Graph(
        nodes=(
            ParseUserIntentNode,
            RetrieveCandidatesNode,
            RerankNode,
            ReturnAnswerNode,
        ),
        state_type=ChatGraphState,
        run_end_type=ChatGraphResult,
    )
