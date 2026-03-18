"""Plain batched search pipeline for retrieval, rerank, and diversification."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter

from ikea_agent.chat.product_images import image_urls_for_runtime
from ikea_agent.chat.runtime import ChatRuntime, embed_queries, search_candidates
from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import (
    RetrievalRequest,
    RetrievalResult,
    SearchBatchToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QueryStageProfile:
    """Timing profile for one query inside a batched search call."""

    retrieval_ms: float
    rerank_ms: float
    diversification_ms: float
    reranker_skipped: bool
    diversification_skipped: bool


async def run_search_pipeline_batch(
    *,
    runtime: ChatRuntime,
    queries: Sequence[SearchQueryInput],
) -> SearchBatchToolResult:
    """Run batched semantic retrieval while preserving per-query rerank/MMR behavior."""

    if not queries:
        raise ValueError("Search queries must not be empty.")

    requests = [_build_request(runtime=runtime, query=query) for query in queries]
    batch_started_at = perf_counter()
    embedding_started_at = perf_counter()
    query_vectors = await embed_queries(runtime, [request.query_text for request in requests])
    embedding_ms = (perf_counter() - embedding_started_at) * 1000.0

    query_results: list[SearchQueryToolResult] = []
    profiles: list[QueryStageProfile] = []
    post_embedding_started_at = perf_counter()
    for query, request, query_vector in zip(queries, requests, query_vectors, strict=True):
        query_result, profile = _execute_query_pipeline(
            runtime=runtime,
            query=query,
            request=request,
            query_vector=query_vector,
        )
        query_results.append(query_result)
        profiles.append(profile)

    post_embedding_ms = (perf_counter() - post_embedding_started_at) * 1000.0
    total_ms = (perf_counter() - batch_started_at) * 1000.0
    logger.info(
        "search_batch_profiled",
        extra={
            "query_count": len(queries),
            "embedding_ms": round(embedding_ms, 3),
            "post_embedding_ms": round(post_embedding_ms, 3),
            "retrieval_ms": round(sum(item.retrieval_ms for item in profiles), 3),
            "rerank_ms": round(sum(item.rerank_ms for item in profiles), 3),
            "diversification_ms": round(sum(item.diversification_ms for item in profiles), 3),
            "reranker_skipped_count": sum(1 for item in profiles if item.reranker_skipped),
            "diversification_skipped_count": sum(
                1 for item in profiles if item.diversification_skipped
            ),
            "total_ms": round(total_ms, 3),
        },
    )

    return SearchBatchToolResult(queries=query_results)


def _execute_query_pipeline(
    *,
    runtime: ChatRuntime,
    query: SearchQueryInput,
    request: RetrievalRequest,
    query_vector: tuple[float, ...],
) -> tuple[SearchQueryToolResult, QueryStageProfile]:
    retrieval_started_at = perf_counter()
    retrieval_results = search_candidates(
        runtime,
        query_vector=query_vector,
        filters=request.filters,
        result_limit=request.result_limit,
    )
    retrieval_ms = (perf_counter() - retrieval_started_at) * 1000.0

    rerank_started_at = perf_counter()
    reranker_skipped = len(retrieval_results) <= 1
    if reranker_skipped:
        reranked_items = _as_reranked_items(retrieval_results)
    else:
        reranked_items = runtime.reranker.rerank(
            query_text=request.query_text,
            results=retrieval_results,
        )
    rerank_ms = (perf_counter() - rerank_started_at) * 1000.0

    diversification_started_at = perf_counter()
    warning: SearchResultDiversityWarning | None = None
    diversification_skipped = (
        not query.enable_diversification or len(reranked_items) <= 1 or query.limit <= 1
    )
    if diversification_skipped:
        selected_results = _select_top_ranked_results(
            reranked_items=reranked_items,
            limit=query.limit,
            runtime=runtime,
        )
    else:
        top_candidate_items = reranked_items[
            : max(query.limit, runtime.settings.mmr_preselect_limit)
        ]
        top_candidate_keys = [item.result.canonical_product_key for item in top_candidate_items]
        similarity_lookup = runtime.catalog_repository.read_neighbor_similarities(
            embedding_model=runtime.settings.gemini_model,
            product_keys=top_candidate_keys,
        )
        diversified = diversify_results(
            reranked_items=reranked_items,
            similarity_lookup=similarity_lookup,
            limit=query.limit,
            lambda_weight=runtime.settings.mmr_lambda,
            preselect_limit=runtime.settings.mmr_preselect_limit,
        )
        selected_results = diversified.results
        warning = diversified.warning
    diversification_ms = (perf_counter() - diversification_started_at) * 1000.0

    logger.info(
        "search_pipeline_completed",
        extra={
            "query": query.semantic_query,
            "query_id": query.query_id,
            "count": len(selected_results),
            "diversification_enabled": query.enable_diversification,
            "retrieval_ms": round(retrieval_ms, 3),
            "rerank_ms": round(rerank_ms, 3),
            "diversification_ms": round(diversification_ms, 3),
            "reranker_skipped": reranker_skipped,
            "diversification_skipped": diversification_skipped,
        },
    )
    return SearchQueryToolResult(
        query_id=query.query_id,
        semantic_query=query.semantic_query,
        results=selected_results,
        warning=warning,
        total_candidates=len(reranked_items),
        returned_count=len(selected_results),
    ), QueryStageProfile(
        retrieval_ms=retrieval_ms,
        rerank_ms=rerank_ms,
        diversification_ms=diversification_ms,
        reranker_skipped=reranker_skipped,
        diversification_skipped=diversification_skipped,
    )


def _build_request(*, runtime: ChatRuntime, query: SearchQueryInput) -> RetrievalRequest:
    default_pool_limit = 300 if query.enable_diversification else 200
    pool_limit = (
        query.candidate_pool_limit if query.candidate_pool_limit is not None else default_pool_limit
    )
    target_limit = max(
        query.limit,
        1,
        pool_limit,
        runtime.settings.default_query_limit,
    )
    return RetrievalRequest(
        query_text=query.semantic_query.strip(),
        result_limit=target_limit,
        filters=query.filters,
    )


def _as_reranked_items(results: list[RetrievalResult]) -> list[RerankedItem]:
    return [
        RerankedItem(
            result=result,
            rank_before=index + 1,
            rank_after=index + 1,
            rerank_score=result.semantic_score,
        )
        for index, result in enumerate(results)
    ]


def _select_top_ranked_results(
    *,
    reranked_items: list[RerankedItem],
    limit: int,
    runtime: ChatRuntime,
) -> list[ShortRetrievalResult]:
    if limit <= 0:
        return []
    selected_results: list[ShortRetrievalResult] = []
    seen_keys: set[str] = set()
    for item in reranked_items:
        key = item.result.canonical_product_key
        if key in seen_keys:
            continue
        selected_results.append(
            item.result.to_short_result(
                image_urls=image_urls_for_runtime(
                    runtime=runtime,
                    canonical_product_key=key,
                )
            )
        )
        seen_keys.add(key)
        if len(selected_results) >= limit:
            break
    return selected_results
