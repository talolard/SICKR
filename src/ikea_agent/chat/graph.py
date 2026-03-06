"""Typed chat graph for parse -> retrieve -> rerank orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from uuid import uuid4

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from ikea_agent.chat.runtime import ChatRuntime, embed_query, search_candidates
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
    result_limit: int | None = None

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Normalize and store the user message in graph state."""

        ctx.state.user_message = self.user_message.strip()
        return RetrieveCandidatesNode(result_limit=self.result_limit)


@dataclass(frozen=True, slots=True)
class RetrieveCandidatesNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Run semantic retrieval against product embeddings."""

    result_limit: int | None = None

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Embed query, run Milvus search, and hydrate candidates from DuckDB."""

        target_limit = (
            max(1, self.result_limit)
            if self.result_limit is not None
            else max(200, ctx.deps.runtime.settings.default_query_limit)
        )
        request = RetrievalRequest(
            query_text=ctx.state.user_message,
            result_limit=target_limit,
            filters=ctx.state.filters or RetrievalFilters(),
        )
        query_vector = await embed_query(ctx.deps.runtime, request.query_text)
        retrieval_results = search_candidates(
            ctx.deps.runtime,
            query_vector=query_vector,
            filters=request.filters,
            result_limit=request.result_limit,
        )

        ctx.state.request_id = str(uuid4())
        return RerankNode(retrieval_results=retrieval_results)


@dataclass(frozen=True, slots=True)
class RerankNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Apply reranking backend to semantic retrieval candidates."""

    retrieval_results: list[RetrievalResult]

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Apply configured reranker backend and project short result rows."""

        reranked_items = ctx.deps.runtime.reranker.rerank(
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
