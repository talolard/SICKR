"""Class-based views for search and shortlist interactions."""

from __future__ import annotations

from urllib.parse import urlencode
from uuid import uuid4

from django.core.paginator import Page, Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.phase3.prompt_lab import PromptLabService
from tal_maria_ikea.phase3.query_expansion import QueryExpansionService
from tal_maria_ikea.phase3.repository import (
    Phase3Repository,
    SearchRequestEvent,
    SearchResultSnapshotRow,
)
from tal_maria_ikea.phase3.reranker import RerankerService
from tal_maria_ikea.retrieval.service import RetrievalService
from tal_maria_ikea.retrieval.shortlist_service import ShortlistService
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    QueryExpansionMode,
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
                "has_pagination": False,
                "page_links": (),
                "low_confidence": False,
                "shortlist": shortlist_service.get_state().items,
                "active_filter_chips": (),
                "expansion_chips": (),
                "expansion_applied": False,
                "show_without_expansion_url": None,
                "rerank_diff_url": None,
                "prompt_lab_url": None,
            }
        )

        if form.is_valid() and form.cleaned_data.get("query_text"):
            settings = get_settings()
            page = form.cleaned_data.get("page") or 1
            expansion_mode = _to_expansion_mode(form.cleaned_data.get("expansion_mode"))
            suppress_expansion = self.request.GET.get("show_without_expansion") == "1"
            expansion_outcome = QueryExpansionService().expand(
                query_text=form.cleaned_data["query_text"],
                mode=expansion_mode,
            )
            expanded_filters = _apply_expanded_filters(
                base_filters=_build_filters(form.cleaned_data),
                extracted=expansion_outcome.extracted_filters,
            )
            effective_filters = (
                _build_filters(form.cleaned_data) if suppress_expansion else expanded_filters
            )
            request = RetrievalRequest(
                query_text=form.cleaned_data["query_text"],
                result_limit=max(200, settings.default_query_limit),
                filters=effective_filters,
            )
            service = RetrievalService()
            execution = service.retrieve_with_trace(request)
            reranked_items = RerankerService().rerank(
                query_text=form.cleaned_data["query_text"],
                results=execution.results,
            )
            results = [item.result for item in reranked_items]
            paginator = Paginator(results, settings.default_query_limit)
            page_obj = paginator.get_page(page)
            context["results"] = list(page_obj.object_list)
            context["page_obj"] = page_obj
            context.update(_build_pagination_context(self.request, page_obj))
            context["active_filter_chips"] = _build_active_filter_chips(form.cleaned_data)
            context["expansion_chips"] = _build_expansion_chips(
                expansion_outcome.extracted_filters,
                applied=bool(expansion_outcome.applied and not suppress_expansion),
            )
            context["expansion_applied"] = bool(
                expansion_outcome.applied and not suppress_expansion
            )
            context["show_without_expansion_url"] = _show_without_expansion_url(self.request)
            context["rerank_diff_url"] = _rerank_diff_url(execution.request_id)
            context["prompt_lab_url"] = _prompt_lab_url(
                request_id=execution.request_id,
                query_text=form.cleaned_data["query_text"],
            )
            context["low_confidence"] = _is_low_confidence(
                results,
                threshold=settings.retrieval_low_confidence_threshold,
            )
            phase3_repository = _phase3_repository()
            phase3_repository.insert_search_request(
                SearchRequestEvent(
                    request_id=execution.request_id,
                    query_text=form.cleaned_data["query_text"],
                    user_ref=None,
                    session_ref=_session_ref(self.request),
                    expansion_mode=expansion_mode,
                    expansion_applied=bool(expansion_outcome.applied and not suppress_expansion),
                    filter_timing_mode="embed_then_filter",
                    rerank_enabled=True,
                    request_source="web",
                    latency_ms=execution.latency_ms,
                )
            )
            phase3_repository.insert_result_snapshots(
                _snapshot_rows_from_results(
                    request_id=execution.request_id,
                    ranking_stage="semantic_before_rerank",
                    results=execution.results,
                    rerank_scores={},
                )
            )
            phase3_repository.insert_result_snapshots(
                _snapshot_rows_from_results(
                    request_id=execution.request_id,
                    ranking_stage="after_rerank",
                    results=results,
                    rerank_scores={
                        item.result.canonical_product_key: item.rerank_score
                        for item in reranked_items
                    },
                )
            )
            phase3_repository.insert_expansion_event(
                expansion_event_id=str(uuid4()),
                request_id=execution.request_id,
                prompt_template_key="expansion-default",
                prompt_template_version="v1",
                expanded_query_text=expansion_outcome.expanded_query_text,
                extracted_filters=expansion_outcome.extracted_filters,
                confidence=expansion_outcome.confidence,
                heuristic_reason=expansion_outcome.heuristic_reason,
                applied=bool(expansion_outcome.applied and not suppress_expansion),
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
        run_sql_file(connection, "sql/42_phase3_runtime.sql")

        total_items_row = connection.execute(
            "SELECT COUNT(*) FROM app.products_market_de_v1"
        ).fetchone()
        total_vectors_row = connection.execute(
            "SELECT COUNT(*) FROM app.product_embeddings_latest"
        ).fetchone()

        context["total_items"] = int(total_items_row[0]) if total_items_row is not None else 0
        context["total_vectors"] = int(total_vectors_row[0]) if total_vectors_row is not None else 0
        return context


class RerankDiffView(TemplateView):
    """Render before/after ranking diff for a query request ID."""

    template_name = "web/rerank_diff.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Load and expose rank-diff rows for one request."""

        context = super().get_context_data(**kwargs)
        request_id = str(kwargs["request_id"])
        rows = _phase3_repository().list_result_diff(request_id=request_id)
        context["request_id"] = request_id
        context["rows"] = rows
        return context


class PromptLabView(TemplateView):
    """Run and display parallel prompt-variant comparison results."""

    template_name = "web/prompt_lab.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Load prompt variants and execution outputs for one request."""

        context = super().get_context_data(**kwargs)
        request_id = str(self.request.GET.get("request_id", "")).strip()
        query_text = str(self.request.GET.get("query_text", "")).strip()
        context["request_id"] = request_id
        context["query_text"] = query_text
        context["results"] = ()
        if not request_id or not query_text:
            return context

        repository = _phase3_repository()
        product_keys = repository.list_result_keys_for_request(request_id=request_id, limit=10)
        results = PromptLabService(repository).run_compare(
            request_id=request_id,
            user_query=query_text,
            product_keys=product_keys,
        )
        context["results"] = results
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


def _to_expansion_mode(value: object) -> QueryExpansionMode:
    if value == "on":
        return "on"
    if value == "off":
        return "off"
    return "auto"


def _build_active_filter_chips(cleaned_data: dict[str, object]) -> tuple[str, ...]:
    chips: list[str] = []
    chips.extend(_category_and_keyword_chips(cleaned_data))
    chips.extend(_sort_and_price_chips(cleaned_data))
    chips.extend(_dimension_chips(cleaned_data))
    return tuple(chips)


def _build_expansion_chips(extracted: dict[str, object], applied: bool) -> tuple[str, ...]:
    if not extracted:
        return ()
    prefix = "AI filter" if applied else "AI suggestion"
    chips: list[str] = []
    for key, value in sorted(extracted.items()):
        chips.append(f"{prefix}: {key}={value}")
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


def _build_pagination_context(
    request: HttpRequest, page_obj: Page
) -> dict[str, bool | tuple[dict[str, int | str | bool], ...]]:
    has_pagination = bool(page_obj.paginator.num_pages > 1)
    page_links = tuple(
        {
            "number": page_number,
            "url": _page_url(request, page_number),
            "is_current": bool(page_number == page_obj.number),
        }
        for page_number in page_obj.paginator.page_range
    )
    return {
        "has_pagination": has_pagination,
        "page_links": page_links,
    }


def _page_url(request: HttpRequest, page_number: int) -> str:
    query = request.GET.copy()
    query["page"] = str(page_number)
    return f"{request.path}?{query.urlencode()}"


def _apply_expanded_filters(
    base_filters: RetrievalFilters, extracted: dict[str, object]
) -> RetrievalFilters:
    category = base_filters.category or _to_optional_str(extracted.get("category"))
    include_keyword = base_filters.include_keyword or _to_optional_str(
        extracted.get("include_keyword")
    )
    exclude_keyword = base_filters.exclude_keyword or _to_optional_str(
        extracted.get("exclude_keyword")
    )
    min_price = base_filters.price.min_eur or _to_optional_float(extracted.get("min_price_eur"))
    max_price = base_filters.price.max_eur or _to_optional_float(extracted.get("max_price_eur"))
    width_max = base_filters.dimensions.width.max_cm or _to_optional_float(
        extracted.get("width_max_cm")
    )

    return RetrievalFilters(
        category=category,
        include_keyword=include_keyword,
        exclude_keyword=exclude_keyword,
        sort=base_filters.sort,
        price=PriceFilterEUR(min_eur=min_price, max_eur=max_price),
        dimensions=DimensionFilter(
            width=DimensionAxisFilter(
                exact_cm=base_filters.dimensions.width.exact_cm,
                min_cm=base_filters.dimensions.width.min_cm,
                max_cm=width_max,
            ),
            depth=base_filters.dimensions.depth,
            height=base_filters.dimensions.height,
        ),
    )


def _show_without_expansion_url(request: HttpRequest) -> str:
    query = request.GET.copy()
    query["show_without_expansion"] = "1"
    return f"{request.path}?{query.urlencode()}"


def _phase3_repository() -> Phase3Repository:
    settings = get_settings()
    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/42_phase3_runtime.sql")
    return Phase3Repository(connection)


def _session_ref(request: HttpRequest) -> str:
    session = getattr(request, "session", None)
    if session is None:
        return "no-session"
    key = session.session_key
    if key is not None:
        return str(key)
    session.save()
    return str(session.session_key)


def _snapshot_rows_from_results(
    *,
    request_id: str,
    ranking_stage: str,
    results: list[RetrievalResult],
    rerank_scores: dict[str, float],
) -> tuple[SearchResultSnapshotRow, ...]:
    return tuple(
        SearchResultSnapshotRow(
            snapshot_id=str(uuid4()),
            request_id=request_id,
            ranking_stage=ranking_stage,
            rank_position=index + 1,
            canonical_product_key=result.canonical_product_key,
            semantic_score=result.semantic_score,
            rerank_score=rerank_scores.get(result.canonical_product_key),
            score_explanation=result.rank_explanation,
        )
        for index, result in enumerate(results)
    )


def _rerank_diff_url(request_id: str) -> str:
    return f"/analysis/rerank-diff/{request_id}"


def _prompt_lab_url(request_id: str, query_text: str) -> str:
    query = urlencode({"request_id": request_id, "query_text": query_text})
    return f"/prompt-lab?{query}"
