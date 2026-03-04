from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi.testclient import TestClient

from tal_maria_ikea.chat.runtime import ChatRuntime
from tal_maria_ikea.chat_app.main import create_app
from tal_maria_ikea.phase3.query_expansion import ExpansionOutcome
from tal_maria_ikea.phase3.repository import ConversationMessageEvent, ConversationMessageRow
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
            low_confidence=False,
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
        self._messages: list[ConversationMessageRow] = []

    def insert_search_request(self, event: object) -> None:
        _ = event

    def insert_result_snapshots(self, rows: object) -> None:
        _ = rows

    def insert_expansion_event(self, **kwargs: object) -> None:
        _ = kwargs

    def upsert_conversation_thread(self, event: object) -> None:
        _ = event

    def insert_conversation_message(self, event: ConversationMessageEvent) -> None:
        self._messages.append(
            ConversationMessageRow(
                message_id="m1",
                conversation_id="chat-req-1",
                role=event.role,
                content_text=event.content_text,
                prompt_run_id=event.prompt_run_id,
                created_at="now",
            )
        )

    def list_results_for_request(
        self, request_id: str, ranking_stage: str = "after_rerank"
    ) -> list[RetrievalResult]:
        _ = (request_id, ranking_stage)
        return [_sample_result()]

    def list_conversation_messages(
        self, conversation_id: str, limit: int = 200
    ) -> tuple[ConversationMessageRow, ...]:
        _ = (conversation_id, limit)
        return tuple(self._messages)


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


def test_healthz() -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        expansion_service=_ExpansionStub(),
        retrieval_service=_RetrievalStub(results=[_sample_result()]),
        reranker_service=_RerankerStub(),
        summary_service=_SummaryStub(),
        phase3_repository=_Phase3RepoStub(),
    )
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_run_and_trace() -> None:
    repository = _Phase3RepoStub()
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        expansion_service=_ExpansionStub(),
        retrieval_service=_RetrievalStub(results=[_sample_result()]),
        reranker_service=_RerankerStub(),
        summary_service=_SummaryStub(),
        phase3_repository=repository,
    )
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    run_response = client.post("/api/chat/run", json={"query_text": "need a lamp"})

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["request_id"] == "req-1"
    assert body["recommended_keys"] == ["1-DE"]

    trace_response = client.get("/api/chat/trace/req-1")

    assert trace_response.status_code == 200
    trace_body = trace_response.json()
    assert trace_body["request_id"] == "req-1"
    assert trace_body["results"][0]["canonical_product_key"] == "1-DE"
    assert len(trace_body["messages"]) >= 1
