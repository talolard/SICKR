"""Plain search pipeline replacing pydantic-graph orchestration."""

from __future__ import annotations

from logging import getLogger

from ikea_agent.chat.runtime import ChatRuntime, embed_query, search_candidates
from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.shared.types import RetrievalFilters, RetrievalRequest, SearchGraphToolResult

logger = getLogger(__name__)


async def run_search_pipeline(
    *,
    runtime: ChatRuntime,
    semantic_query: str,
    limit: int = 20,
    candidate_pool_limit: int | None = None,
    filters: RetrievalFilters | None = None,
) -> SearchGraphToolResult:
    """Run semantic retrieval, reranking, and diversification without graph state."""

    target_limit = max(
        limit,
        1,
        candidate_pool_limit or 0,
        200,
        runtime.settings.default_query_limit,
    )
    request = RetrievalRequest(
        query_text=semantic_query.strip(),
        result_limit=target_limit,
        filters=filters or RetrievalFilters(),
    )
    query_vector = await embed_query(runtime, request.query_text)
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
    top_candidate_items = reranked_items[: max(limit, runtime.settings.mmr_preselect_limit)]
    top_candidate_keys = [item.result.canonical_product_key for item in top_candidate_items]
    similarity_lookup = runtime.catalog_repository.read_neighbor_similarities(
        embedding_model=runtime.settings.gemini_model,
        product_keys=top_candidate_keys,
    )
    diversified = diversify_results(
        reranked_items=reranked_items,
        similarity_lookup=similarity_lookup,
        limit=limit,
        lambda_weight=runtime.settings.mmr_lambda,
        preselect_limit=runtime.settings.mmr_preselect_limit,
    )
    logger.info(
        "search_pipeline_completed",
        extra={"query": semantic_query, "count": len(diversified.results)},
    )
    return SearchGraphToolResult(
        results=diversified.results,
        warning=diversified.warning,
        total_candidates=len(reranked_items),
        returned_count=len(diversified.results),
    )
