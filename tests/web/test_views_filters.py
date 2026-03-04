from __future__ import annotations

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpRequest, QueryDict

from tal_maria_ikea.shared.types import RetrievalResult
from tal_maria_ikea.web.views import _build_filters, _build_pagination_context, _is_low_confidence


def test_build_filters_maps_numeric_fields() -> None:
    cleaned = {
        "category": "tables-desks",
        "include_keyword": "soft",
        "exclude_keyword": "spotlight",
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
    assert filters.include_keyword == "soft"
    assert filters.exclude_keyword == "spotlight"
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


def test_build_pagination_context_preserves_existing_query_params() -> None:
    if not settings.configured:
        settings.configure(DEFAULT_CHARSET="utf-8")

    request = HttpRequest()
    request.path = "/"
    request.GET = QueryDict(
        "query_text=Closet&exclude_keyword=frame&min_price_eur=10&page=2",
        mutable=False,
        encoding="utf-8",
    )
    page_obj = Paginator([1, 2, 3], per_page=1).get_page(2)

    context = _build_pagination_context(request, page_obj)

    assert context["has_pagination"] is True
    page_links = context["page_links"]
    assert page_links == (
        {
            "number": 1,
            "url": "/?query_text=Closet&exclude_keyword=frame&min_price_eur=10&page=1",
            "is_current": False,
        },
        {
            "number": 2,
            "url": "/?query_text=Closet&exclude_keyword=frame&min_price_eur=10&page=2",
            "is_current": True,
        },
        {
            "number": 3,
            "url": "/?query_text=Closet&exclude_keyword=frame&min_price_eur=10&page=3",
            "is_current": False,
        },
    )
