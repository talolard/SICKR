from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import cast

import pytest

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat.search_pipeline import run_search_pipeline_batch
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import (
    RetrievalFilters,
    RetrievalResult,
    SearchQueryInput,
    SearchQueryToolResult,
)


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25
    gemini_model: str = "gemini-embedding-001"
    mmr_lambda: float = 0.8
    mmr_preselect_limit: int = 30
    embedding_query_batch_size: int = 16


@dataclass(slots=True)
class _CatalogStub:
    neighbor_similarity_calls: list[list[str]] = field(default_factory=list)

    def read_neighbor_similarities(
        self,
        *,
        embedding_model: str,
        product_keys: list[str],
    ) -> dict[tuple[str, str], float]:
        _ = embedding_model
        self.neighbor_similarity_calls.append(product_keys)
        return {}


@dataclass(frozen=True, slots=True)
class _ProductImageCatalogStub:
    image_urls: tuple[str, ...] = ()

    def image_urls_for_canonical_key(self, *, canonical_product_key: str) -> tuple[str, ...]:
        _ = canonical_product_key
        return self.image_urls


@dataclass(slots=True)
class _RerankerSpy:
    calls: list[tuple[str, int]] = field(default_factory=list)

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        self.calls.append((query_text, len(results)))
        return [
            RerankedItem(
                result=result,
                rank_before=index + 1,
                rank_after=index + 1,
                rerank_score=result.semantic_score,
            )
            for index, result in enumerate(results)
        ]


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    settings: _SettingsStub
    reranker: _RerankerSpy
    catalog_repository: _CatalogStub
    product_image_catalog: _ProductImageCatalogStub


@dataclass(slots=True)
class _SearchCandidatesSpy:
    responses: list[list[RetrievalResult]]
    result_limits: list[int] = field(default_factory=list)

    def __call__(
        self,
        runtime: ChatRuntime,
        *,
        query_vector: tuple[float, ...],
        filters: object,
        result_limit: int,
    ) -> list[RetrievalResult]:
        _ = (runtime, query_vector, filters)
        self.result_limits.append(result_limit)
        return self.responses.pop(0)


@dataclass(slots=True)
class _EmbedQueriesSpy:
    calls: list[list[str]] = field(default_factory=list)

    async def __call__(
        self,
        runtime: ChatRuntime,
        query_texts: list[str],
    ) -> list[tuple[float, float, float]]:
        _ = runtime
        self.calls.append(query_texts)
        return [(0.1, 0.2, 0.3) for _ in query_texts]


def _sample_result(
    *,
    product_id: str = "1-DE",
    product_name: str = "Lamp",
    product_type: str = "Lamp",
) -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key=product_id,
        product_name=product_name,
        product_type=product_type,
        description_text=f"{product_name} description",
        embedding_text=None,
        main_category="lighting",
        sub_category="lamps",
        dimensions_text="10x10x20",
        width_cm=10.0,
        depth_cm=10.0,
        height_cm=20.0,
        price_eur=29.99,
        url=f"https://example.com/{product_id}",
        semantic_score=0.8,
        filter_pass_reasons=("ok",),
        rank_explanation="score",
    )


def _runtime() -> _RuntimeStub:
    return _RuntimeStub(
        settings=_SettingsStub(),
        reranker=_RerankerSpy(),
        catalog_repository=_CatalogStub(),
        product_image_catalog=_ProductImageCatalogStub(image_urls=("/static/product-images/1",)),
    )


def _run_single_query_batch(
    *,
    runtime: _RuntimeStub,
    semantic_query: str,
    limit: int = 20,
    candidate_pool_limit: int | None = None,
    filters: RetrievalFilters | None = None,
    enable_diversification: bool = True,
) -> SearchQueryToolResult:
    return asyncio.run(
        run_search_pipeline_batch(
            runtime=cast("ChatRuntime", runtime),
            queries=[
                SearchQueryInput(
                    query_id="query-1",
                    semantic_query=semantic_query,
                    limit=limit,
                    candidate_pool_limit=candidate_pool_limit,
                    filters=filters or RetrievalFilters(),
                    enable_diversification=enable_diversification,
                )
            ],
        )
    ).queries[0]


def test_search_pipeline_returns_empty_matches_when_no_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(responses=[[]])
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = _run_single_query_batch(
        runtime=runtime,
        semantic_query="need a couch",
        enable_diversification=False,
    )

    assert output.results == []
    assert output.total_candidates == 0
    assert output.returned_count == 0
    assert embed_spy.calls == [["need a couch"]]


def test_search_pipeline_returns_ranked_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(responses=[[_sample_result()]])
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = _run_single_query_batch(
        runtime=runtime,
        semantic_query="need a lamp",
        enable_diversification=False,
    )

    assert len(output.results) == 1
    assert output.results[0].product_id == "1-DE"
    assert output.results[0].product_name == "Lamp"
    assert output.results[0].product_type == "Lamp"
    assert output.results[0].image_urls == ("/static/product-images/1",)
    assert output.total_candidates == 1
    assert search_spy.result_limits == [200]


def test_search_pipeline_uses_candidate_pool_limit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(responses=[[_sample_result()]])
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    _ = _run_single_query_batch(
        runtime=runtime,
        semantic_query="need a lamp",
        limit=20,
        candidate_pool_limit=280,
    )

    assert search_spy.result_limits == [280]


def test_search_pipeline_batch_embeds_queries_in_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(
        responses=[
            [_sample_result(product_id="1-DE", product_name="Desk lamp")],
            [_sample_result(product_id="2-DE", product_name="Reading chair", product_type="Chair")],
        ]
    )
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = asyncio.run(
        run_search_pipeline_batch(
            runtime=cast("ChatRuntime", runtime),
            queries=[
                SearchQueryInput(
                    query_id="lighting",
                    semantic_query="desk lamp",
                    enable_diversification=False,
                ),
                SearchQueryInput(
                    query_id="seating",
                    semantic_query="reading chair",
                    enable_diversification=False,
                    filters=RetrievalFilters(category="chairs"),
                ),
            ],
        )
    )

    assert embed_spy.calls == [["desk lamp", "reading chair"]]
    assert [query.query_id for query in output.queries] == ["lighting", "seating"]
    assert output.queries[0].results[0].product_name == "Desk lamp"
    assert output.queries[1].results[0].product_name == "Reading chair"
    assert search_spy.result_limits == [200, 200]


def test_search_pipeline_skips_reranker_for_single_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(responses=[[_sample_result()]])
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = asyncio.run(
        run_search_pipeline_batch(
            runtime=cast("ChatRuntime", runtime),
            queries=[
                SearchQueryInput(
                    query_id="lighting",
                    semantic_query="desk lamp",
                    enable_diversification=True,
                )
            ],
        )
    )

    assert runtime.reranker.calls == []
    assert runtime.catalog_repository.neighbor_similarity_calls == []
    assert output.queries[0].results[0].product_name == "Lamp"


def test_search_pipeline_batch_rejects_empty_query_list() -> None:
    runtime = _runtime()

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(
            run_search_pipeline_batch(
                runtime=cast("ChatRuntime", runtime),
                queries=[],
            )
        )


def test_search_pipeline_diversification_uses_reranker_and_neighbor_similarities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    search_spy = _SearchCandidatesSpy(
        responses=[[_sample_result(product_id="1-DE"), _sample_result(product_id="2-DE")]]
    )
    embed_spy = _EmbedQueriesSpy()

    monkeypatch.setattr("ikea_agent.chat.search_pipeline.embed_queries", embed_spy)
    monkeypatch.setattr("ikea_agent.chat.search_pipeline.search_candidates", search_spy)

    output = asyncio.run(
        run_search_pipeline_batch(
            runtime=cast("ChatRuntime", runtime),
            queries=[
                SearchQueryInput(
                    query_id="lighting",
                    semantic_query="desk lamp",
                    enable_diversification=True,
                )
            ],
        )
    )

    assert runtime.reranker.calls == [("desk lamp", 2)]
    assert runtime.catalog_repository.neighbor_similarity_calls == [["1-DE", "2-DE"]]
    assert [result.product_id for result in output.queries[0].results] == ["1-DE", "2-DE"]
