"""Class-based views for search and shortlist interactions."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.retrieval.service import RetrievalService
from tal_maria_ikea.retrieval.shortlist_service import ShortlistService
from tal_maria_ikea.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResult,
)
from tal_maria_ikea.web.forms import SearchForm, ShortlistNoteForm


class SearchView(TemplateView):
    """Render search page and query results."""

    template_name = "web/search.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Build context for GET render."""

        context = super().get_context_data(**kwargs)
        form = SearchForm(self.request.GET or None)
        shortlist_service = ShortlistService()
        context.update(
            {
                "form": form,
                "results": [],
                "page_obj": None,
                "low_confidence": False,
                "shortlist": shortlist_service.get_state().items,
            }
        )

        if form.is_valid() and form.cleaned_data.get("query_text"):
            settings = get_settings()
            page = form.cleaned_data.get("page") or 1
            request = RetrievalRequest(
                query_text=form.cleaned_data["query_text"],
                result_limit=max(200, settings.default_query_limit),
                filters=_build_filters(form.cleaned_data),
            )
            service = RetrievalService()
            results = service.retrieve(request)
            paginator = Paginator(results, settings.default_query_limit)
            page_obj = paginator.get_page(page)
            context["results"] = list(page_obj.object_list)
            context["page_obj"] = page_obj
            context["low_confidence"] = _is_low_confidence(
                results,
                threshold=settings.retrieval_low_confidence_threshold,
            )

        return context


class ShortlistAddView(View):
    """Handle shortlist add action."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Add one product key to global shortlist and redirect."""

        canonical_product_key = request.POST.get("canonical_product_key")
        if isinstance(canonical_product_key, str) and canonical_product_key:
            form = ShortlistNoteForm(request.POST)
            note = form.cleaned_data["note"] if form.is_valid() else None
            ShortlistService().add(canonical_product_key, note)
        return redirect("web:search")


class ShortlistRemoveView(View):
    """Handle shortlist remove action."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Remove one product key from global shortlist and redirect."""

        canonical_product_key = request.POST.get("canonical_product_key")
        if isinstance(canonical_product_key, str) and canonical_product_key:
            ShortlistService().remove(canonical_product_key)
        return redirect("web:search")


def _build_filters(cleaned_data: dict[str, object]) -> RetrievalFilters:
    """Map form fields to retrieval filter dataclasses."""

    return RetrievalFilters(
        category=_to_optional_str(cleaned_data.get("category")),
        price=PriceFilterEUR(
            min_eur=_to_optional_float(cleaned_data.get("min_price_eur")),
            max_eur=_to_optional_float(cleaned_data.get("max_price_eur")),
        ),
        dimensions=DimensionFilter(
            width=DimensionAxisFilter(
                exact_cm=_to_optional_float(cleaned_data.get("width_exact_cm")),
                min_cm=_to_optional_float(cleaned_data.get("width_min_cm")),
                max_cm=_to_optional_float(cleaned_data.get("width_max_cm")),
            ),
            depth=DimensionAxisFilter(
                exact_cm=_to_optional_float(cleaned_data.get("depth_exact_cm")),
                min_cm=_to_optional_float(cleaned_data.get("depth_min_cm")),
                max_cm=_to_optional_float(cleaned_data.get("depth_max_cm")),
            ),
            height=DimensionAxisFilter(
                exact_cm=_to_optional_float(cleaned_data.get("height_exact_cm")),
                min_cm=_to_optional_float(cleaned_data.get("height_min_cm")),
                max_cm=_to_optional_float(cleaned_data.get("height_max_cm")),
            ),
        ),
    )


def _to_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _is_low_confidence(results: list[RetrievalResult], threshold: float | None = None) -> bool:
    if not results:
        return True

    top_result = results[0]
    top_score = top_result.semantic_score
    if threshold is None:
        settings = get_settings()
        threshold = settings.retrieval_low_confidence_threshold
    return bool(top_score < threshold)
