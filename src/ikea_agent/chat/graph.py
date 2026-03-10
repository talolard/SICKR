"""Typed chat graph for parse -> retrieve -> rerank -> MMR orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from uuid import uuid4

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from ikea_agent.chat.runtime import ChatRuntime, embed_query, search_candidates
from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.shared.types import (
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResult,
    SearchResultDiversityWarning,
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
    total_candidates: int
    warning: SearchResultDiversityWarning | None


@dataclass(frozen=True, slots=True)
class ParseUserIntentNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Initialize graph state for one incoming user chat message."""

    user_message: str
    result_limit: int = 20
    candidate_pool_limit: int | None = None

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Normalize and store the user message in graph state."""

        ctx.state.user_message = self.user_message.strip()
        return RetrieveCandidatesNode(
            result_limit=self.result_limit,
            candidate_pool_limit=self.candidate_pool_limit,
        )


@dataclass(frozen=True, slots=True)
class RetrieveCandidatesNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Run semantic retrieval against product embeddings."""

    result_limit: int
    candidate_pool_limit: int | None = None

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Embed query, run Milvus search, and hydrate candidates from DuckDB."""

        target_limit = max(
            self.result_limit,
            1,
            self.candidate_pool_limit or 0,
            200,
            ctx.deps.runtime.settings.default_query_limit,
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
        return RerankNode(
            retrieval_results=retrieval_results,
            result_limit=self.result_limit,
        )


@dataclass(frozen=True, slots=True)
class RerankNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Apply reranking backend and MMR diversification to candidates."""

    retrieval_results: list[RetrievalResult]
    result_limit: int

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Apply configured reranker backend and project short result rows."""

        reranked_items = ctx.deps.runtime.reranker.rerank(
            query_text=ctx.state.user_message,
            results=self.retrieval_results,
        )
        top_candidate_items = reranked_items[
            : max(self.result_limit, ctx.deps.runtime.settings.mmr_preselect_limit)
        ]
        top_candidate_keys = [item.result.canonical_product_key for item in top_candidate_items]
        similarity_lookup = ctx.deps.runtime.catalog_repository.read_neighbor_similarities(
            embedding_model=ctx.deps.runtime.settings.gemini_model,
            product_keys=top_candidate_keys,
        )
        diversified = diversify_results(
            reranked_items=reranked_items,
            similarity_lookup=similarity_lookup,
            limit=self.result_limit,
            lambda_weight=ctx.deps.runtime.settings.mmr_lambda,
            preselect_limit=ctx.deps.runtime.settings.mmr_preselect_limit,
        )
        return ReturnAnswerNode(
            reranked_results=diversified.results,
            total_candidates=len(reranked_items),
            warning=diversified.warning,
        )


@dataclass(frozen=True, slots=True)
class ReturnAnswerNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Return final graph payload to HTTP or agent callers."""

    reranked_results: list[ShortRetrievalResult]
    total_candidates: int
    warning: SearchResultDiversityWarning | None

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> End[ChatGraphResult]:
        """Finalize graph output payload."""

        logger.info("chat_answer_ready based on %d results", len(self.reranked_results))
        return End(
            ChatGraphResult(
                request_id=ctx.state.request_id,
                product_matches=self.reranked_results,
                total_candidates=self.total_candidates,
                warning=self.warning,
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
