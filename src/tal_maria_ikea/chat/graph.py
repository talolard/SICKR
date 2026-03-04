"""Typed chat graph for search -> summarize -> refine orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from tal_maria_ikea.chat.runtime import ChatRuntime
from tal_maria_ikea.phase3.query_expansion import ExpansionOutcome
from tal_maria_ikea.phase3.repository import (
    ConversationMessageEvent,
    ConversationThreadEvent,
    SearchRequestEvent,
    SearchResultSnapshotRow,
)
from tal_maria_ikea.phase3.search_summary import SearchSummaryExecution, SummaryCandidateProduct
from tal_maria_ikea.shared.types import (
    QueryExpansionMode,
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResult,
)


@dataclass(frozen=True, slots=True)
class ChatGraphDeps:
    """Typed dependency container used by all graph nodes."""

    runtime: ChatRuntime


@dataclass(slots=True)
class ChatGraphState:
    """Mutable graph state shared between chat pipeline nodes."""

    user_message: str = ""
    expansion_mode: QueryExpansionMode = "auto"
    base_filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    effective_filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    expansion_outcome: ExpansionOutcome | None = None
    retrieval_results: list[RetrievalResult] = field(default_factory=list)
    reranked_results: list[RetrievalResult] = field(default_factory=list)
    rerank_scores: dict[str, float] = field(default_factory=dict)
    request_id: str = ""
    low_confidence: bool = True
    summary_execution: SearchSummaryExecution | None = None
    answer_text: str = ""
    needs_clarification: bool = False
    conversation_id: str = ""


@dataclass(frozen=True, slots=True)
class ChatGraphResult:
    """Final typed payload returned by the chat graph."""

    request_id: str
    conversation_id: str
    answer_text: str
    needs_clarification: bool
    recommended_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParseUserIntentNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Initialize graph state for one incoming user chat message."""

    user_message: str
    expansion_mode: QueryExpansionMode = "auto"
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Seed state fields from the incoming user request."""

        ctx.state.user_message = self.user_message.strip()
        ctx.state.expansion_mode = self.expansion_mode
        ctx.state.base_filters = self.filters
        ctx.state.effective_filters = self.filters
        return ExpandQueryNode()


@dataclass(frozen=True, slots=True)
class ExpandQueryNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Extract optional structured constraints from the user message."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Apply heuristic/model query expansion and merge extracted filters."""

        outcome = ctx.deps.runtime.expansion_service.expand(
            query_text=ctx.state.user_message,
            mode=ctx.state.expansion_mode,
        )
        ctx.state.expansion_outcome = outcome
        if outcome.applied:
            ctx.state.effective_filters = _apply_expanded_filters(
                base_filters=ctx.state.base_filters,
                extracted=outcome.extracted_filters,
            )
        return RetrieveCandidatesNode()


@dataclass(frozen=True, slots=True)
class RetrieveCandidatesNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Run semantic retrieval against product embeddings."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Execute retrieval request and store request metadata."""

        request = RetrievalRequest(
            query_text=ctx.state.user_message,
            result_limit=max(200, ctx.deps.runtime.settings.default_query_limit),
            filters=ctx.state.effective_filters,
        )
        execution = ctx.deps.runtime.retrieval_service.retrieve_with_trace(request, source="chat")
        ctx.state.request_id = execution.request_id
        ctx.state.retrieval_results = execution.results
        ctx.state.low_confidence = execution.low_confidence
        return RerankNode()


@dataclass(frozen=True, slots=True)
class RerankNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Apply reranking backend to semantic retrieval candidates."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Run reranking backend and keep rerank scores by product key."""

        reranked_items = ctx.deps.runtime.reranker_service.rerank(
            query_text=ctx.state.user_message,
            results=ctx.state.retrieval_results,
        )
        ctx.state.reranked_results = [item.result for item in reranked_items]
        ctx.state.rerank_scores = {
            item.result.canonical_product_key: item.rerank_score for item in reranked_items
        }
        return SummarizeNode()


@dataclass(frozen=True, slots=True)
class SummarizeNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Generate structured summary over reranked candidates."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Build structured summary over top reranked products."""

        if not ctx.state.reranked_results:
            ctx.state.summary_execution = None
            return RefineResponseNode()

        products = tuple(
            SummaryCandidateProduct(
                canonical_product_key=result.canonical_product_key,
                item_name=result.product_name,
            )
            for result in ctx.state.reranked_results[:50]
        )
        ctx.state.summary_execution = ctx.deps.runtime.summary_service.generate(
            request_id=ctx.state.request_id,
            query_text=ctx.state.user_message,
            products=products,
            template_key="summary-default",
            template_version="v1",
        )
        return RefineResponseNode()


@dataclass(frozen=True, slots=True)
class RefineResponseNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Build final user-facing answer text from the pipeline outputs."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Transform structured outputs into user-facing answer text."""

        if not ctx.state.reranked_results:
            ctx.state.needs_clarification = True
            ctx.state.answer_text = (
                "I could not find relevant IKEA products yet. "
                "Could you add one or two concrete constraints like category, size, or budget?"
            )
            return PersistTelemetryNode()

        if ctx.state.low_confidence:
            ctx.state.needs_clarification = True

        top_items = ctx.state.reranked_results[:3]
        if ctx.state.summary_execution is None:
            summary_text = (
                f"Top matches for '{ctx.state.user_message}' are shown below from the reranked set."
            )
        else:
            summary_text = ctx.state.summary_execution.response.summary

        lines = [summary_text, "", "Top picks:"]
        for result in top_items:
            price_text = f"€{result.price_eur:.2f}" if result.price_eur is not None else "price n/a"
            lines.append(f"- {result.product_name} ({result.canonical_product_key}) · {price_text}")
        if ctx.state.needs_clarification:
            lines.append("")
            lines.append("If you share tighter constraints, I can refine these further.")
        ctx.state.answer_text = "\n".join(lines)
        return PersistTelemetryNode()


@dataclass(frozen=True, slots=True)
class PersistTelemetryNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Persist request snapshots and conversation messages for traceability."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
        """Persist telemetry, snapshots, and conversation turn history."""

        repository = ctx.deps.runtime.phase3_repository
        request_id = ctx.state.request_id
        repository.insert_search_request(
            SearchRequestEvent(
                request_id=request_id,
                query_text=ctx.state.user_message,
                user_ref=None,
                session_ref=None,
                expansion_mode=ctx.state.expansion_mode,
                expansion_applied=bool(
                    ctx.state.expansion_outcome and ctx.state.expansion_outcome.applied
                ),
                filter_timing_mode="embed_then_filter",
                rerank_enabled=True,
                request_source="chat",
                latency_ms=None,
            )
        )
        repository.insert_result_snapshots(
            _snapshot_rows_from_results(
                request_id=request_id,
                ranking_stage="semantic_before_rerank",
                results=ctx.state.retrieval_results,
                rerank_scores={},
            )
        )
        repository.insert_result_snapshots(
            _snapshot_rows_from_results(
                request_id=request_id,
                ranking_stage="after_rerank",
                results=ctx.state.reranked_results,
                rerank_scores=ctx.state.rerank_scores,
            )
        )

        outcome = ctx.state.expansion_outcome
        repository.insert_expansion_event(
            expansion_event_id=str(uuid4()),
            request_id=request_id,
            prompt_template_key="expansion-default",
            prompt_template_version="v1",
            expanded_query_text=None if outcome is None else outcome.expanded_query_text,
            extracted_filters={} if outcome is None else outcome.extracted_filters,
            confidence=0.0 if outcome is None else outcome.confidence,
            heuristic_reason=None if outcome is None else outcome.heuristic_reason,
            applied=bool(outcome and outcome.applied),
        )

        ctx.state.conversation_id = f"chat-{request_id}"
        repository.upsert_conversation_thread(
            ConversationThreadEvent(
                conversation_id=ctx.state.conversation_id,
                request_id=request_id,
                user_ref=None,
                session_ref=None,
                title=f"Chat request {request_id[:8]}",
                is_active=True,
            )
        )
        repository.insert_conversation_message(
            ConversationMessageEvent(
                message_id=str(uuid4()),
                conversation_id=ctx.state.conversation_id,
                role="user",
                content_text=ctx.state.user_message,
                prompt_run_id=None,
            )
        )
        repository.insert_conversation_message(
            ConversationMessageEvent(
                message_id=str(uuid4()),
                conversation_id=ctx.state.conversation_id,
                role="assistant",
                content_text=ctx.state.answer_text,
                prompt_run_id=(
                    None
                    if ctx.state.summary_execution is None
                    else ctx.state.summary_execution.prompt_run_id
                ),
            )
        )
        return ReturnAnswerNode()


@dataclass(frozen=True, slots=True)
class ReturnAnswerNode(BaseNode[ChatGraphState, ChatGraphDeps, ChatGraphResult]):
    """Return final graph payload to HTTP or agent callers."""

    async def run(
        self, ctx: GraphRunContext[ChatGraphState, ChatGraphDeps]
    ) -> End[ChatGraphResult]:
        """Produce typed terminal output from current graph state."""

        return End(
            ChatGraphResult(
                request_id=ctx.state.request_id,
                conversation_id=ctx.state.conversation_id,
                answer_text=ctx.state.answer_text,
                needs_clarification=ctx.state.needs_clarification,
                recommended_keys=tuple(
                    item.canonical_product_key for item in ctx.state.reranked_results[:5]
                ),
            )
        )


def build_chat_graph() -> Graph[ChatGraphState, ChatGraphDeps, ChatGraphResult]:
    """Create chat graph instance with explicit node registry."""

    return Graph(
        nodes=(
            ParseUserIntentNode,
            ExpandQueryNode,
            RetrieveCandidatesNode,
            RerankNode,
            SummarizeNode,
            RefineResponseNode,
            PersistTelemetryNode,
            ReturnAnswerNode,
        ),
        state_type=ChatGraphState,
        run_end_type=ChatGraphResult,
    )


def _snapshot_rows_from_results(
    *,
    request_id: str,
    ranking_stage: str,
    results: list[RetrievalResult],
    rerank_scores: dict[str, float],
) -> tuple[SearchResultSnapshotRow, ...]:
    return tuple(
        SearchResultSnapshotRow(
            snapshot_id=str(uuid4()),
            request_id=request_id,
            ranking_stage=ranking_stage,
            rank_position=index + 1,
            canonical_product_key=result.canonical_product_key,
            semantic_score=result.semantic_score,
            rerank_score=rerank_scores.get(result.canonical_product_key),
            score_explanation=result.rank_explanation,
        )
        for index, result in enumerate(results)
    )


def _apply_expanded_filters(
    *,
    base_filters: RetrievalFilters,
    extracted: dict[str, object],
) -> RetrievalFilters:
    category = _pick_str(base_filters.category, extracted.get("category"))
    include_keyword = _pick_str(base_filters.include_keyword, extracted.get("include_keyword"))
    exclude_keyword = _pick_str(base_filters.exclude_keyword, extracted.get("exclude_keyword"))
    min_price = _pick_float(base_filters.price.min_eur, extracted.get("min_price_eur"))
    max_price = _pick_float(base_filters.price.max_eur, extracted.get("max_price_eur"))
    width_max = _pick_float(base_filters.dimensions.width.max_cm, extracted.get("width_max_cm"))

    return RetrievalFilters(
        category=category,
        include_keyword=include_keyword,
        exclude_keyword=exclude_keyword,
        sort=base_filters.sort,
        price=base_filters.price.__class__(min_eur=min_price, max_eur=max_price),
        dimensions=base_filters.dimensions.__class__(
            width=base_filters.dimensions.width.__class__(
                exact_cm=base_filters.dimensions.width.exact_cm,
                min_cm=base_filters.dimensions.width.min_cm,
                max_cm=width_max,
            ),
            depth=base_filters.dimensions.depth,
            height=base_filters.dimensions.height,
        ),
    )


def _pick_str(current_value: str | None, candidate: object) -> str | None:
    if current_value is not None:
        return current_value
    if not isinstance(candidate, str):
        return None
    cleaned = candidate.strip()
    return cleaned or None


def _pick_float(current_value: float | None, candidate: object) -> float | None:
    if current_value is not None:
        return current_value
    if not isinstance(candidate, int | float):
        return None
    return float(candidate)
