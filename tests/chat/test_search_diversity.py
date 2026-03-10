from __future__ import annotations

from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import RetrievalResult


def _result(product_id: str, product_name: str, semantic_score: float) -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key=product_id,
        product_name=product_name,
        product_type="Storage",
        description_text=f"{product_name} storage unit",
        embedding_text=None,
        main_category="Storage",
        sub_category="Children's storage",
        dimensions_text="50x30x40",
        width_cm=50.0,
        depth_cm=30.0,
        height_cm=40.0,
        price_eur=49.99,
        url=None,
        semantic_score=semantic_score,
        filter_pass_reasons=("ok",),
        rank_explanation="score",
    )


def _item(
    product_id: str,
    product_name: str,
    rerank_score: float,
    rank: int,
) -> RerankedItem:
    result = _result(product_id=product_id, product_name=product_name, semantic_score=rerank_score)
    return RerankedItem(
        result=result,
        rank_before=rank,
        rank_after=rank,
        rerank_score=rerank_score,
    )


def test_diversify_results_uses_mmr_penalty_to_avoid_redundant_pick() -> None:
    reranked = [
        _item("trofast-1", "TROFAST frame", rerank_score=0.99, rank=1),
        _item("trofast-2", "TROFAST combination", rerank_score=0.95, rank=2),
        _item("kallax-1", "KALLAX shelf", rerank_score=0.93, rank=3),
        _item("billy-1", "BILLY shelf", rerank_score=0.70, rank=4),
    ]
    similarities = {
        ("trofast-1", "trofast-2"): 0.98,
        ("trofast-2", "trofast-1"): 0.98,
        ("trofast-1", "kallax-1"): 0.05,
        ("kallax-1", "trofast-1"): 0.05,
    }

    diversified = diversify_results(
        reranked_items=reranked,
        similarity_lookup=similarities,
        limit=2,
        lambda_weight=0.8,
        preselect_limit=4,
    )

    assert [item.product_id for item in diversified.results] == ["trofast-1", "kallax-1"]


def test_diversify_results_emits_warning_for_high_family_concentration() -> None:
    reranked = [
        _item("trofast-1", "TROFAST frame", rerank_score=0.99, rank=1),
        _item("trofast-2", "TROFAST shelf", rerank_score=0.98, rank=2),
        _item("trofast-3", "TROFAST tray", rerank_score=0.97, rank=3),
        _item("kallax-1", "KALLAX shelf", rerank_score=0.40, rank=4),
    ]

    diversified = diversify_results(
        reranked_items=reranked,
        similarity_lookup={},
        limit=4,
        lambda_weight=1.0,
        preselect_limit=4,
    )

    assert diversified.warning is not None
    assert diversified.warning.kind == "high_family_concentration"
    assert diversified.warning.dominant_family == "trofast"
    assert diversified.warning.analyzed_result_count == 4
