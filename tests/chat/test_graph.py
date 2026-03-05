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
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.retrieval.service import VectorMatch
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25
    retrieval_candidate_limit: int = 250
    gemini_model: str = "gemini-embedding-001"


class _EmbedderStub:
    async def embed_query(self, query_text: str) -> object:
        _ = query_text

        @dataclass(frozen=True, slots=True)
        class _Response:
            embeddings: list[tuple[float, ...]]

        return _Response(embeddings=[(0.1, 0.2, 0.3)])


class _MilvusStub:
    def search(
        self,
        *,
        query_vector: tuple[float, ...],
        embedding_model: str,
        candidate_limit: int,
    ) -> list[VectorMatch]:
        _ = (query_vector, embedding_model, candidate_limit)
        return [VectorMatch(canonical_product_key="1-DE", semantic_score=0.8)]


class _CatalogStub:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def hydrate_candidates(
        self,
        *,
        candidates: list[VectorMatch],
        filters: RetrievalFilters,
        result_limit: int,
    ) -> list[RetrievalResult]:
        _ = (candidates, filters, result_limit)
        return self._results


class _RerankerStub:
    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        _ = query_text
        return [
            RerankedItem(
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
    embedder: _EmbedderStub
    milvus_service: _MilvusStub
    catalog_repository: _CatalogStub
    reranker: _RerankerStub


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
        embedder=_EmbedderStub(),
        milvus_service=_MilvusStub(),
        catalog_repository=_CatalogStub(results=[]),
        reranker=_RerankerStub(),
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a couch"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.request_id != ""
    assert output.product_matches == []


def test_graph_returns_ranked_results() -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        embedder=_EmbedderStub(),
        milvus_service=_MilvusStub(),
        catalog_repository=_CatalogStub(results=[_sample_result()]),
        reranker=_RerankerStub(),
    )
    graph = build_chat_graph()

    output = graph.run_sync(
        ParseUserIntentNode(user_message="need a lamp"),
        state=ChatGraphState(),
        deps=ChatGraphDeps(runtime=cast("ChatRuntime", runtime)),
    ).output

    assert output.request_id != ""
    assert len(output.product_matches) == 1
    assert output.product_matches[0].product_id == "1-DE"
