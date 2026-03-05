from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ikea_agent.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.retrieval.service import RetrievalExecution
from ikea_agent.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25


class _RetrievalStub:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    async def retrieve_with_trace(self, request: object, source: str) -> RetrievalExecution:
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


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    settings: _SettingsStub
    retrieval_service: _RetrievalStub
    reranker_service: _RerankerStub


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


def test_graph_returns_empty_matches_when_no_results() -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        retrieval_service=_RetrievalStub(results=[]),
        reranker_service=_RerankerStub(),
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a couch"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.request_id == "req-1"
    assert output.product_matches == []


def test_graph_returns_ranked_results() -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        retrieval_service=_RetrievalStub(results=[_sample_result()]),
        reranker_service=_RerankerStub(),
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a lamp"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.request_id == "req-1"
    assert len(output.product_matches) == 1
    assert output.product_matches[0].product_id == "1-DE"
