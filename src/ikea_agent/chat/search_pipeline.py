"""Plain search pipeline replacing pydantic-graph orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from logging import getLogger

from ikea_agent.chat.runtime import ChatRuntime, embed_queries, search_candidates
from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import (
    RetrievalFilters,
    RetrievalRequest,
    SearchBatchToolResult,
    SearchGraphToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)

logger = getLogger(__name__)


async def run_search_pipeline(
    *,
    runtime: ChatRuntime,
    semantic_query: str,
    limit: int = 20,
    candidate_pool_limit: int | None = None,
    filters: RetrievalFilters | None = None,
    enable_diversification: bool = True,
) -> SearchGraphToolResult:
    """Run one query through the batched search pipeline for compatibility."""

    output = await run_search_pipeline_batch(
        runtime=runtime,
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
    first_query = output.queries[0]
    return SearchGraphToolResult(
        results=first_query.results,
        warning=first_query.warning,
        total_candidates=first_query.total_candidates,
        returned_count=first_query.returned_count,
    )


async def run_search_pipeline_batch(
    *,
    runtime: ChatRuntime,
    queries: Sequence[SearchQueryInput],
) -> SearchBatchToolResult:
    """Run batched semantic retrieval while preserving per-query rerank/MMR behavior."""

    if not queries:
        raise ValueError("Search queries must not be empty.")

    requests = [_build_request(runtime=runtime, query=query) for query in queries]
    query_vectors = await embed_queries(runtime, [request.query_text for request in requests])

    query_results: list[SearchQueryToolResult] = []
    for query, request, query_vector in zip(queries, requests, query_vectors, strict=True):
        retrieval_results = search_candidates(
            runtime,
            query_vector=query_vector,
            filters=request.filters,
            result_limit=request.result_limit,
        )
        reranked_items = runtime.reranker.rerank(
            query_text=request.query_text,
            results=retrieval_results,
        )
        warning: SearchResultDiversityWarning | None = None
        selected_results: list[ShortRetrievalResult]
        if query.enable_diversification:
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
        else:
            selected_results = _select_top_ranked_results(
                reranked_items=reranked_items,
                limit=query.limit,
            )
        logger.info(
            "search_pipeline_completed",
            extra={
                "query": query.semantic_query,
                "query_id": query.query_id,
                "count": len(selected_results),
                "diversification_enabled": query.enable_diversification,
            },
        )
        query_results.append(
            SearchQueryToolResult(
                query_id=query.query_id,
                semantic_query=query.semantic_query,
                results=selected_results,
                warning=warning,
                total_candidates=len(reranked_items),
                returned_count=len(selected_results),
            )
        )

    return SearchBatchToolResult(queries=query_results)


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


def _select_top_ranked_results(
    *, reranked_items: list[RerankedItem], limit: int
) -> list[ShortRetrievalResult]:
    if limit <= 0:
        return []
    selected_results: list[ShortRetrievalResult] = []
    seen_keys: set[str] = set()
    for item in reranked_items:
        key = item.result.canonical_product_key
        if key in seen_keys:
            continue
        selected_results.append(item.result.to_short_result())
        seen_keys.add(key)
        if len(selected_results) >= limit:
            break
    return selected_results
