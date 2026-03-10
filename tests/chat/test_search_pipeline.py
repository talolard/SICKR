from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

import pytest

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat.search_pipeline import run_search_pipeline
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25
    gemini_model: str = "gemini-embedding-001"
    mmr_lambda: float = 0.8
    mmr_preselect_limit: int = 30


class _CatalogStub:
    def read_neighbor_similarities(
        self,
        *,
        embedding_model: str,
        product_keys: list[str],
    ) -> dict[tuple[str, str], float]:
        _ = (embedding_model, product_keys)
        return {}


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
    reranker: _RerankerStub
    catalog_repository: _CatalogStub


@dataclass(slots=True)
class _SearchCandidatesSpy:
    results: list[RetrievalResult]
    last_result_limit: int | None = None

    def __call__(
        self,
        runtime: ChatRuntime,
        *,
        query_vector: tuple[float, ...],
        filters: object,
        result_limit: int,
    ) -> list[RetrievalResult]:
        _ = (runtime, query_vector, filters)
        self.last_result_limit = result_limit
        return self.results


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


def test_search_pipeline_returns_empty_matches_when_no_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        reranker=_RerankerStub(),
        catalog_repository=_CatalogStub(),
    )
    search_spy = _SearchCandidatesSpy(results=[])

    async def _embed_query(runtime: ChatRuntime, query_text: str) -> tuple[float, float, float]:
        _ = (runtime, query_text)
        return (0.1, 0.2, 0.3)

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_query", _embed_query)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = asyncio.run(
        run_search_pipeline(
            runtime=cast("ChatRuntime", runtime),
            semantic_query="need a couch",
        )
    )

    assert output.results == []
    assert output.total_candidates == 0
    assert output.returned_count == 0


def test_search_pipeline_returns_ranked_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        reranker=_RerankerStub(),
        catalog_repository=_CatalogStub(),
    )
    search_spy = _SearchCandidatesSpy(results=[_sample_result()])

    async def _embed_query(runtime: ChatRuntime, query_text: str) -> tuple[float, float, float]:
        _ = (runtime, query_text)
        return (0.1, 0.2, 0.3)

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_query", _embed_query)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = asyncio.run(
        run_search_pipeline(
            runtime=cast("ChatRuntime", runtime),
            semantic_query="need a lamp",
        )
    )

    assert len(output.results) == 1
    assert output.results[0].product_id == "1-DE"
    assert output.results[0].product_name == "Lamp"
    assert output.results[0].product_type == "Lamp"
    assert output.total_candidates == 1
    assert search_spy.last_result_limit == 200


def test_search_pipeline_uses_candidate_pool_limit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _RuntimeStub(
        settings=_SettingsStub(),
        reranker=_RerankerStub(),
        catalog_repository=_CatalogStub(),
    )
    search_spy = _SearchCandidatesSpy(results=[_sample_result()])

    async def _embed_query(runtime: ChatRuntime, query_text: str) -> tuple[float, float, float]:
        _ = (runtime, query_text)
        return (0.1, 0.2, 0.3)

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_query", _embed_query)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    _ = asyncio.run(
        run_search_pipeline(
            runtime=cast("ChatRuntime", runtime),
            semantic_query="need a lamp",
            limit=20,
            candidate_pool_limit=280,
        )
    )

    assert search_spy.last_result_limit == 280
