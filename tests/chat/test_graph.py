from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tal_maria_ikea.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from tal_maria_ikea.chat.runtime import ChatRuntime
from tal_maria_ikea.phase3.query_expansion import ExpansionOutcome
from tal_maria_ikea.phase3.search_summary import (
    SearchSummaryExecution,
    SearchSummaryItem,
    SearchSummaryResponse,
)
from tal_maria_ikea.retrieval.service import RetrievalExecution
from tal_maria_ikea.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25


class _ExpansionStub:
    def expand(self, query_text: str, mode: str) -> ExpansionOutcome:
        _ = (query_text, mode)
        return ExpansionOutcome(
            expanded_query_text=None,
            extracted_filters={},
            confidence=0.0,
            heuristic_reason="none",
            applied=False,
            provider="heuristic",
        )


class _RetrievalStub:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def retrieve_with_trace(self, request: object, source: str) -> RetrievalExecution:
        _ = (request, source)
        return RetrievalExecution(
            request_id="req-1",
            results=self._results,
            latency_ms=10,
            low_confidence=not bool(self._results),
        )


class _RerankerStub:
    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[object]:
        _ = query_text

        @dataclass(frozen=True, slots=True)
        class _Item:
            result: RetrievalResult
            rank_before: int
            rank_after: int
            rerank_score: float

        return [
            _Item(
                result=result,
                rank_before=i + 1,
                rank_after=i + 1,
                rerank_score=result.semantic_score,
            )
            for i, result in enumerate(results)
        ]


class _SummaryStub:
    def generate(self, **kwargs: object) -> SearchSummaryExecution:
        _ = kwargs
        response = SearchSummaryResponse(
            summary="Summary text",
            items=[
                SearchSummaryItem(
                    canonical_product_key="1-DE",
                    item_name="Lamp",
                    why="relevant",
                )
            ],
        )
        return SearchSummaryExecution(
            prompt_run_id="run-1",
            turn_id="turn-1",
            rendered_system_prompt="system",
            generation_config_json="{}",
            response=response,
        )


class _Phase3RepoStub:
    def __init__(self) -> None:
        self.saved_messages = 0

    def insert_search_request(self, event: object) -> None:
        _ = event

    def insert_result_snapshots(self, rows: object) -> None:
        _ = rows

    def insert_expansion_event(self, **kwargs: object) -> None:
        _ = kwargs

    def upsert_conversation_thread(self, event: object) -> None:
        _ = event

    def insert_conversation_message(self, event: object) -> None:
        _ = event
        self.saved_messages += 1


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    settings: _SettingsStub
    expansion_service: _ExpansionStub
    retrieval_service: _RetrievalStub
    reranker_service: _RerankerStub
    summary_service: _SummaryStub
    phase3_repository: _Phase3RepoStub


def _sample_result() -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key="1-DE",
        product_name="Lamp",
        product_type="Lamp",
        description_text="Bright lamp",
        embedding_text=None,
        main_category="lighting",
        sub_category="lamps",
        dimensions_text="10x10x20",
        width_cm=10.0,
        depth_cm=10.0,
        height_cm=20.0,
        price_eur=29.99,
        url="https://example.com/1",
        semantic_score=0.8,
        filter_pass_reasons=("ok",),
        rank_explanation="score",
    )


def test_graph_returns_clarification_when_no_results() -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        expansion_service=_ExpansionStub(),
        retrieval_service=_RetrievalStub(results=[]),
        reranker_service=_RerankerStub(),
        summary_service=_SummaryStub(),
        phase3_repository=_Phase3RepoStub(),
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a couch"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.needs_clarification is True
    assert "Could you add" in output.answer_text


def test_graph_returns_ranked_answer_and_persists_messages() -> None:
    repository = _Phase3RepoStub()
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        expansion_service=_ExpansionStub(),
        retrieval_service=_RetrievalStub(results=[_sample_result()]),
        reranker_service=_RerankerStub(),
        summary_service=_SummaryStub(),
        phase3_repository=repository,
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a lamp"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.needs_clarification is False
    assert "Top picks" in output.answer_text
    assert output.recommended_keys == ("1-DE",)
    assert repository.saved_messages == 2
