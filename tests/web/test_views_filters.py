from __future__ import annotations

from tal_maria_ikea.shared.types import RetrievalResult
from tal_maria_ikea.web.views import _build_filters, _is_low_confidence


def test_build_filters_maps_numeric_fields() -> None:
    cleaned = {
        "category": "tables-desks",
        "sort": "price_asc",
        "min_price_eur": 10.0,
        "max_price_eur": 200.0,
        "exact_dimensions": True,
        "width_exact_cm": 120.0,
        "width_min_cm": 100.0,
        "width_max_cm": 140.0,
        "depth_exact_cm": None,
        "depth_min_cm": 50.0,
        "depth_max_cm": 70.0,
        "height_exact_cm": None,
        "height_min_cm": 60.0,
        "height_max_cm": 90.0,
    }

    filters = _build_filters(cleaned)

    assert filters.category == "tables-desks"
    assert filters.sort == "price_asc"
    assert filters.price.min_eur == 10.0
    assert filters.dimensions.width.exact_cm == 120.0
    assert filters.dimensions.width.min_cm == 100.0
    assert filters.dimensions.depth.max_cm == 70.0


def test_is_low_confidence_true_for_empty_results() -> None:
    assert _is_low_confidence([], threshold=0.15) is True


def test_is_low_confidence_uses_top_score_threshold() -> None:
    high = RetrievalResult(
        canonical_product_key="1-DE",
        product_name="Desk",
        product_type="Desk",
        description_text="desc",
        embedding_text="embedding text",
        main_category="tables-desks",
        sub_category="desks",
        dimensions_text="120x60x75 cm",
        width_cm=120.0,
        depth_cm=60.0,
        height_cm=75.0,
        price_eur=99.0,
        url="https://example.com/1",
        semantic_score=0.9,
        filter_pass_reasons=("structured_filters_passed",),
        rank_explanation="semantic cosine score 0.9",
    )

    assert _is_low_confidence([high], threshold=0.15) is False
