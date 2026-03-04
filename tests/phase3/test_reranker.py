from __future__ import annotations

from tal_maria_ikea.phase3.reranker import RerankerService
from tal_maria_ikea.shared.types import RetrievalResult


def _result(
    key: str,
    name: str,
    description: str,
    score: float,
) -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key=key,
        product_name=name,
        product_type=name,
        description_text=description,
        embedding_text=description,
        main_category="lighting",
        sub_category="lamps",
        dimensions_text=None,
        width_cm=None,
        depth_cm=None,
        height_cm=None,
        price_eur=None,
        url=None,
        semantic_score=score,
        filter_pass_reasons=("structured_filters_passed",),
        rank_explanation=f"semantic cosine score {score}",
    )


def test_reranker_reorders_by_query_overlap() -> None:
    service = RerankerService()
    results = [
        _result("2-DE", "Curtain Set", "blackout curtain for hallway", 0.98),
        _result("1-DE", "Desk Lamp", "bright desk lamp", 0.40),
    ]

    reranked = service.rerank("desk lamp", results)

    assert reranked[0].result.canonical_product_key == "1-DE"
    assert reranked[0].rank_before == 2
    assert reranked[0].rank_after == 1
