from __future__ import annotations

from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.shared.types import ShortRetrievalResult


def _result(product_id: str, product_name: str) -> ShortRetrievalResult:
    return ShortRetrievalResult(
        product_id=product_id,
        product_name=product_name,
        product_type="Storage",
        description_text=f"{product_name} storage unit",
        main_category="Storage",
        sub_category="Children's storage",
        width_cm=50.0,
        depth_cm=30.0,
        height_cm=40.0,
        price_eur=49.99,
    )


def test_diversify_results_round_robins_families() -> None:
    results = [
        _result("trofast-1", "TROFAST frame"),
        _result("trofast-2", "TROFAST combination"),
        _result("kallax-1", "KALLAX shelf"),
        _result("alex-1", "ALEX drawer unit"),
    ]

    diversified = diversify_results(results=results, limit=3)

    assert [item.product_name for item in diversified.results] == [
        "TROFAST frame",
        "KALLAX shelf",
        "ALEX drawer unit",
    ]
    assert diversified.warning is None


def test_diversify_results_emits_warning_for_dominant_family() -> None:
    results = [
        _result("trofast-1", "TROFAST frame"),
        _result("trofast-2", "TROFAST combination"),
        _result("trofast-3", "TROFAST shelf"),
        _result("trofast-4", "TROFAST tray"),
        _result("kallax-1", "KALLAX shelf"),
    ]

    diversified = diversify_results(results=results, limit=5)

    assert diversified.warning is not None
    assert diversified.warning.kind == "high_family_concentration"
    assert diversified.warning.dominant_family == "trofast"
    assert diversified.warning.analyzed_result_count == 5
