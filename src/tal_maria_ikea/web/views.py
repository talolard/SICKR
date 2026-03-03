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
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResult,
    SortMode,
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
                "active_filter_chips": (),
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
            context["active_filter_chips"] = _build_active_filter_chips(form.cleaned_data)
            context["low_confidence"] = _is_low_confidence(
                results,
                threshold=settings.retrieval_low_confidence_threshold,
            )

        return context


class StatsView(TemplateView):
    """Render dataset statistics used by the UI."""

    template_name = "web/stats.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Load and expose item/vector totals for the stats dashboard."""

        context = super().get_context_data(**kwargs)
        settings = get_settings()
        connection = connect_db(settings.duckdb_path)
        run_sql_file(connection, "sql/10_schema.sql")
        run_sql_file(connection, "sql/14_market_views.sql")
        run_sql_file(connection, "sql/22_embedding_store.sql")

        total_items_row = connection.execute(
            "SELECT COUNT(*) FROM app.products_market_de_v1"
        ).fetchone()
        total_vectors_row = connection.execute(
            "SELECT COUNT(*) FROM app.product_embeddings_latest"
        ).fetchone()

        context["total_items"] = int(total_items_row[0]) if total_items_row is not None else 0
        context["total_vectors"] = int(total_vectors_row[0]) if total_vectors_row is not None else 0
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
        include_keyword=_to_optional_str(cleaned_data.get("include_keyword")),
        exclude_keyword=_to_optional_str(cleaned_data.get("exclude_keyword")),
        sort=_to_sort_mode(cleaned_data.get("sort")),
        price=PriceFilterEUR(
            min_eur=_to_optional_float(cleaned_data.get("min_price_eur")),
            max_eur=_to_optional_float(cleaned_data.get("max_price_eur")),
        ),
        dimensions=DimensionFilter(
            width=DimensionAxisFilter(
                exact_cm=_axis_exact(cleaned_data, "width_exact_cm"),
                min_cm=_to_optional_float(cleaned_data.get("width_min_cm")),
                max_cm=_to_optional_float(cleaned_data.get("width_max_cm")),
            ),
            depth=DimensionAxisFilter(
                exact_cm=_axis_exact(cleaned_data, "depth_exact_cm"),
                min_cm=_to_optional_float(cleaned_data.get("depth_min_cm")),
                max_cm=_to_optional_float(cleaned_data.get("depth_max_cm")),
            ),
            height=DimensionAxisFilter(
                exact_cm=_axis_exact(cleaned_data, "height_exact_cm"),
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


def _axis_exact(cleaned_data: dict[str, object], key: str) -> float | None:
    if not bool(cleaned_data.get("exact_dimensions")):
        return None
    return _to_optional_float(cleaned_data.get(key))


def _to_sort_mode(value: object) -> SortMode:
    if value == "price_asc":
        return "price_asc"
    if value == "price_desc":
        return "price_desc"
    if value == "size":
        return "size"
    return "relevance"


def _build_active_filter_chips(cleaned_data: dict[str, object]) -> tuple[str, ...]:
    chips: list[str] = []
    chips.extend(_category_and_keyword_chips(cleaned_data))
    chips.extend(_sort_and_price_chips(cleaned_data))
    chips.extend(_dimension_chips(cleaned_data))
    return tuple(chips)


def _category_and_keyword_chips(cleaned_data: dict[str, object]) -> tuple[str, ...]:
    chips: list[str] = []
    category = _to_optional_str(cleaned_data.get("category"))
    if category is not None:
        chips.append(f"Category: {_humanize_category(category)}")

    include_keyword = _to_optional_str(cleaned_data.get("include_keyword"))
    if include_keyword is not None:
        chips.append(f"Must include: {include_keyword}")

    exclude_keyword = _to_optional_str(cleaned_data.get("exclude_keyword"))
    if exclude_keyword is not None:
        chips.append(f"Must exclude: {exclude_keyword}")
    return tuple(chips)


def _sort_and_price_chips(cleaned_data: dict[str, object]) -> tuple[str, ...]:
    chips: list[str] = []
    sort = _to_sort_mode(cleaned_data.get("sort"))
    if sort != "relevance":
        chips.append(f"Sort: {sort.replace('_', ' ')}")

    min_price = _to_optional_float(cleaned_data.get("min_price_eur"))
    max_price = _to_optional_float(cleaned_data.get("max_price_eur"))
    if min_price is not None or max_price is not None:
        chips.append(f"Price: €{_display_price(min_price)} - €{_display_price(max_price)}")
    return tuple(chips)


def _dimension_chips(cleaned_data: dict[str, object]) -> tuple[str, ...]:
    chips: list[str] = []
    if bool(cleaned_data.get("exact_dimensions")):
        chips.append("Dimensions: exact mode")

    for axis in ("width", "depth", "height"):
        exact = _axis_exact(cleaned_data, f"{axis}_exact_cm")
        min_value = _to_optional_float(cleaned_data.get(f"{axis}_min_cm"))
        max_value = _to_optional_float(cleaned_data.get(f"{axis}_max_cm"))
        label = axis.capitalize()
        if exact is not None:
            chips.append(f"{label}: {exact:g} cm")
        elif min_value is not None or max_value is not None:
            chips.append(f"{label}: {_display_price(min_value)}-{_display_price(max_value)} cm")
    return tuple(chips)


def _humanize_category(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip().title()


def _display_price(value: float | None) -> str:
    if value is None:
        return "any"
    return f"{value:g}"


def _is_low_confidence(results: list[RetrievalResult], threshold: float | None = None) -> bool:
    if not results:
        return True

    top_result = results[0]
    top_score = top_result.semantic_score
    if threshold is None:
        settings = get_settings()
        threshold = settings.retrieval_low_confidence_threshold
    return bool(top_score < threshold)
