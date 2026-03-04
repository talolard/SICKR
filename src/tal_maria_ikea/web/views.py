"""Class-based views for search and shortlist interactions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlencode
from uuid import uuid4

from django.core.paginator import Page, Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView
from pydantic import ValidationError

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.phase3.conversation import ConversationService
from tal_maria_ikea.phase3.prompt_lab import PromptLabService
from tal_maria_ikea.phase3.query_expansion import ExpansionOutcome, QueryExpansionService
from tal_maria_ikea.phase3.repository import (
    ItemRatingEvent,
    Phase3Repository,
    ResultDiffRow,
    SearchRequestEvent,
    SearchResultSnapshotRow,
    TurnRatingEvent,
)
from tal_maria_ikea.phase3.reranker import RerankerService
from tal_maria_ikea.phase3.search_summary import (
    SearchSummaryResponse,
    SearchSummaryService,
    SummaryCandidateProduct,
)
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
from tal_maria_ikea.web.forms import (
    FollowUpForm,
    ItemFeedbackForm,
    SearchForm,
    ShortlistNoteForm,
    TurnFeedbackForm,
)


class SearchView(TemplateView):
    """Render search page and query results."""

    template_name = "web/search.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Build context for GET render."""

        context = super().get_context_data(**kwargs)
        form = SearchForm(self.request.GET or None)
        context.update(_empty_search_context(form=form))
        context["shortlist"] = ShortlistService().get_state().items
        if form.is_valid() and form.cleaned_data.get("query_text"):
            payload = _build_search_payload(
                request=self.request,
                cleaned_data=form.cleaned_data,
            )
            context.update(_search_payload_to_context(request=self.request, payload=payload))
        return context


class SearchResultsPartialView(View):
    """Render HTMX search results without full-page reload."""

    template_name = "web/partials/search_results.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render only results region content for HTMX GET requests."""

        form = SearchForm(request.GET or None)
        if not form.is_valid() or not form.cleaned_data.get("query_text"):
            context = _empty_search_context(form=form)
            return render(request, self.template_name, context)
        payload = _build_search_payload(request=request, cleaned_data=form.cleaned_data)
        context = _search_payload_to_context(request=request, payload=payload)
        return render(request, self.template_name, context)


class SearchSummaryPartialView(View):
    """Render one async summary block for a completed search request."""

    template_name = "web/partials/search_summary.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render async summary block, using cache when available."""

        request_id = _to_optional_str(request.GET.get("request_id"))
        query_signature_hash = _to_optional_str(request.GET.get("query_signature_hash"))
        query_text = _to_optional_str(request.GET.get("query_text"))
        template_key = (
            _to_optional_str(request.GET.get("summary_template_key")) or "summary-default"
        )
        template_version = _to_optional_str(request.GET.get("summary_template_version")) or "v1"
        if request_id is None or query_signature_hash is None or query_text is None:
            return render(
                request,
                self.template_name,
                {"summary": None, "summary_items": (), "summary_status": "missing_params"},
            )

        repository = _phase3_repository()
        ranked_results = repository.list_results_for_request(
            request_id=request_id, ranking_stage="after_rerank"
        )
        products = tuple(
            SummaryCandidateProduct(
                canonical_product_key=result.canonical_product_key,
                item_name=result.product_name,
            )
            for result in ranked_results[:50]
        )
        if not products:
            return render(
                request,
                self.template_name,
                {"summary": None, "summary_items": (), "summary_status": "no_results"},
            )

        resultset_hash = _resultset_hash(products)
        summary_config_hash = _summary_config_hash(
            template_key=template_key,
            template_version=template_version,
        )
        summary_cache_key = _summary_cache_key(
            query_signature_hash=query_signature_hash,
            resultset_hash=resultset_hash,
            summary_config_hash=summary_config_hash,
        )
        summary_cache_row = repository.get_summary_cache(
            summary_cache_key=summary_cache_key,
            summary_config_hash=summary_config_hash,
        )

        cached = _load_cached_summary(
            repository=repository,
            summary_json=summary_cache_row.summary_json if summary_cache_row else None,
            summary_cache_key=summary_cache_key,
            request_id=request_id,
            query_signature_hash=query_signature_hash,
            resultset_hash=resultset_hash,
            summary_config_hash=summary_config_hash,
            products=products,
        )
        if cached is not None:
            return render(
                request,
                self.template_name,
                {
                    "summary": cached.summary,
                    "summary_items": tuple(cached.items),
                    "summary_status": "cache_hit",
                },
            )

        execution = SearchSummaryService(repository).generate(
            request_id=request_id,
            query_text=query_text,
            products=products,
            template_key=template_key,
            template_version=template_version,
        )
        repository.upsert_summary_cache(
            summary_cache_key=summary_cache_key,
            request_id=request_id,
            query_signature_hash=query_signature_hash,
            resultset_hash=resultset_hash,
            summary_config_hash=summary_config_hash,
            summary_json=execution.response.model_dump_json(),
            ttl_hours=24,
        )
        return render(
            request,
            self.template_name,
            {
                "summary": execution.response.summary,
                "summary_items": tuple(execution.response.items),
                "summary_status": "generated",
            },
        )


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
        phase3_repository = Phase3Repository(connection)
        context["turn_feedback_summary"] = phase3_repository.summarize_turn_feedback()
        context["item_feedback_summary"] = phase3_repository.summarize_item_feedback()
        return context


class RerankDiffView(TemplateView):
    """Render before/after ranking diff for a query request ID."""

    template_name = "web/rerank_diff.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Load and expose rank-diff rows for one request."""

        context = super().get_context_data(**kwargs)
        request_id = str(kwargs["request_id"])
        rows = _phase3_repository().list_result_diff(request_id=request_id)
        changed_rows, unchanged_count = _split_changed_and_unchanged(rows)
        context["request_id"] = request_id
        context["rows"] = changed_rows
        context["unchanged_count"] = unchanged_count
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
        context["conversation_id"] = f"compare-{request_id}" if request_id else ""
        context["results"] = ()
        if not request_id or not query_text:
            return context

        repository = _phase3_repository()
        ranked_results = repository.list_results_for_request(
            request_id=request_id, ranking_stage="after_rerank"
        )
        candidates = tuple(
            (result.canonical_product_key, result.product_name) for result in ranked_results[:10]
        )
        if not candidates:
            return context
        results = PromptLabService(repository).run_compare(
            request_id=request_id,
            user_query=query_text,
            candidates=candidates,
        )
        context["results"] = results
        return context


class ConversationView(View):
    """Render one conversation thread and handle follow-up posts."""

    template_name = "web/conversation.html"

    def get(self, request: HttpRequest, conversation_id: str) -> HttpResponse:
        """Render one conversation thread page."""

        repository = _phase3_repository()
        return render(
            request,
            self.template_name,
            {
                "conversation_id": conversation_id,
                "threads": repository.list_conversation_threads(limit=50),
                "messages": repository.list_conversation_messages(
                    conversation_id=conversation_id,
                    limit=200,
                ),
                "form": FollowUpForm(),
            },
        )

    def post(self, request: HttpRequest, conversation_id: str) -> HttpResponse:
        """Persist follow-up message and assistant response, then redirect."""

        form = FollowUpForm(request.POST)
        if form.is_valid():
            ConversationService(_phase3_repository()).append_follow_up(
                conversation_id=conversation_id,
                prompt_run_id=_to_optional_str(form.cleaned_data.get("prompt_run_id")),
                user_message=str(form.cleaned_data["user_message"]),
            )
        return redirect(_conversation_url(conversation_id))


class TurnFeedbackView(View):
    """Persist turn-level feedback events."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Validate and store one turn feedback submission."""

        form = TurnFeedbackForm(request.POST)
        if form.is_valid():
            _phase3_repository().insert_turn_rating(
                TurnRatingEvent(
                    turn_rating_id=str(uuid4()),
                    turn_id=str(form.cleaned_data["turn_id"]),
                    request_id=str(form.cleaned_data["request_id"]),
                    prompt_run_id=str(form.cleaned_data["prompt_run_id"]),
                    thumb=str(form.cleaned_data["thumb"]),
                    reason_tags=_parse_reason_tags(form.cleaned_data.get("reason_tags")),
                    note=_to_optional_str(form.cleaned_data.get("note")),
                    user_ref=None,
                    session_ref=_session_ref(request),
                )
            )
        return redirect(_prompt_lab_redirect(request))


class ItemFeedbackView(View):
    """Persist item-level feedback events."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Validate and store one item feedback submission."""

        form = ItemFeedbackForm(request.POST)
        if form.is_valid():
            _phase3_repository().insert_item_rating(
                ItemRatingEvent(
                    item_rating_id=str(uuid4()),
                    turn_id=str(form.cleaned_data["turn_id"]),
                    request_id=str(form.cleaned_data["request_id"]),
                    prompt_run_id=str(form.cleaned_data["prompt_run_id"]),
                    canonical_product_key=str(form.cleaned_data["canonical_product_key"]),
                    thumb=str(form.cleaned_data["thumb"]),
                    reason_tags=_parse_reason_tags(form.cleaned_data.get("reason_tags")),
                    note=_to_optional_str(form.cleaned_data.get("note")),
                    user_ref=None,
                    session_ref=_session_ref(request),
                )
            )
        return redirect(_prompt_lab_redirect(request))


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


@dataclass(frozen=True, slots=True)
class SearchPayload:
    """Normalized search execution output used by full and HTMX views."""

    query_text: str
    request_id: str
    query_signature_hash: str
    page_obj: Page
    paginated_results: list[RetrievalResult]
    all_results: list[RetrievalResult]
    active_filter_chips: tuple[str, ...]
    expansion_chips: tuple[str, ...]
    expansion_applied: bool
    show_without_expansion_url: str
    rerank_diff_url: str
    prompt_lab_url: str
    low_confidence: bool


def _empty_search_context(form: SearchForm) -> dict[str, object]:
    """Return baseline template context for empty/invalid search state."""

    return {
        "form": form,
        "results": [],
        "page_obj": None,
        "has_pagination": False,
        "page_links": (),
        "low_confidence": False,
        "active_filter_chips": (),
        "expansion_chips": (),
        "expansion_applied": False,
        "show_without_expansion_url": None,
        "rerank_diff_url": None,
        "prompt_lab_url": None,
        "request_id": "",
        "query_signature_hash": "",
        "query_text": "",
        "summary_url": None,
    }


def _build_search_payload(
    *, request: HttpRequest, cleaned_data: dict[str, object]
) -> SearchPayload:
    """Execute retrieval flow with query cache and return normalized payload."""

    settings = get_settings()
    query_text = str(cleaned_data["query_text"])
    page_value = cleaned_data.get("page")
    page = int(page_value) if isinstance(page_value, int | float | str) else 1
    expansion_mode = _to_expansion_mode(cleaned_data.get("expansion_mode"))
    suppress_expansion = request.GET.get("show_without_expansion") == "1"
    expansion_outcome = QueryExpansionService().expand(
        query_text=query_text,
        mode=expansion_mode,
    )
    base_filters = _build_filters(cleaned_data)
    expanded_filters = _apply_expanded_filters(
        base_filters=base_filters,
        extracted=expansion_outcome.extracted_filters,
    )
    effective_filters = base_filters if suppress_expansion else expanded_filters

    query_signature_hash = _query_signature_hash(
        cleaned_data=cleaned_data, suppress=suppress_expansion
    )
    cache_config_hash = _query_cache_config_hash()
    repository = _phase3_repository()
    query_cache_row = repository.get_query_cache(
        query_signature_hash=query_signature_hash,
        cache_config_hash=cache_config_hash,
    )

    if query_cache_row is None:
        request_id = _run_search_and_persist(
            http_request=request,
            repository=repository,
            query_text=query_text,
            effective_filters=effective_filters,
            expansion_mode=expansion_mode,
            suppress_expansion=suppress_expansion,
            expansion_outcome=expansion_outcome,
        )
        repository.upsert_query_cache(
            query_signature_hash=query_signature_hash,
            request_id=request_id,
            query_text=query_text,
            filters_json=json.dumps(cleaned_data, sort_keys=True, default=str),
            cache_config_hash=cache_config_hash,
            ttl_hours=24,
        )
    else:
        request_id = query_cache_row.request_id

    all_results = repository.list_results_for_request(
        request_id=request_id, ranking_stage="after_rerank"
    )
    paginator = Paginator(all_results, settings.default_query_limit)
    page_obj = paginator.get_page(page)
    paginated_results = list(page_obj.object_list)

    return SearchPayload(
        query_text=query_text,
        request_id=request_id,
        query_signature_hash=query_signature_hash,
        page_obj=page_obj,
        paginated_results=paginated_results,
        all_results=all_results,
        active_filter_chips=_build_active_filter_chips(cleaned_data),
        expansion_chips=_build_expansion_chips(
            expansion_outcome.extracted_filters,
            applied=bool(expansion_outcome.applied and not suppress_expansion),
        ),
        expansion_applied=bool(expansion_outcome.applied and not suppress_expansion),
        show_without_expansion_url=_show_without_expansion_url(request),
        rerank_diff_url=_rerank_diff_url(request_id),
        prompt_lab_url=_prompt_lab_url(request_id=request_id, query_text=query_text),
        low_confidence=_is_low_confidence(
            all_results,
            threshold=settings.retrieval_low_confidence_threshold,
        ),
    )


def _run_search_and_persist(
    *,
    http_request: HttpRequest,
    repository: Phase3Repository,
    query_text: str,
    effective_filters: RetrievalFilters,
    expansion_mode: QueryExpansionMode,
    suppress_expansion: bool,
    expansion_outcome: ExpansionOutcome,
) -> str:
    """Execute retrieval+rereank pipeline and persist request snapshots."""

    settings = get_settings()
    request_payload = RetrievalRequest(
        query_text=query_text,
        result_limit=max(200, settings.default_query_limit),
        filters=effective_filters,
    )
    execution = RetrievalService().retrieve_with_trace(request_payload)
    reranked_items = RerankerService().rerank(
        query_text=query_text,
        results=execution.results,
    )
    reranked_results = [item.result for item in reranked_items]
    repository.insert_search_request(
        SearchRequestEvent(
            request_id=execution.request_id,
            query_text=query_text,
            user_ref=None,
            session_ref=_session_ref(http_request),
            expansion_mode=expansion_mode,
            expansion_applied=bool(expansion_outcome.applied and not suppress_expansion),
            filter_timing_mode="embed_then_filter",
            rerank_enabled=True,
            request_source="web",
            latency_ms=execution.latency_ms,
        )
    )
    repository.insert_result_snapshots(
        _snapshot_rows_from_results(
            request_id=execution.request_id,
            ranking_stage="semantic_before_rerank",
            results=execution.results,
            rerank_scores={},
        )
    )
    repository.insert_result_snapshots(
        _snapshot_rows_from_results(
            request_id=execution.request_id,
            ranking_stage="after_rerank",
            results=reranked_results,
            rerank_scores={
                item.result.canonical_product_key: item.rerank_score for item in reranked_items
            },
        )
    )
    repository.insert_expansion_event(
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
    return execution.request_id


def _search_payload_to_context(request: HttpRequest, payload: SearchPayload) -> dict[str, object]:
    """Map one payload object to template context fields."""

    context: dict[str, object] = {
        "results": payload.paginated_results,
        "page_obj": payload.page_obj,
        "request_id": payload.request_id,
        "query_text": payload.query_text,
        "query_signature_hash": payload.query_signature_hash,
        "active_filter_chips": payload.active_filter_chips,
        "expansion_chips": payload.expansion_chips,
        "expansion_applied": payload.expansion_applied,
        "show_without_expansion_url": payload.show_without_expansion_url,
        "rerank_diff_url": payload.rerank_diff_url,
        "prompt_lab_url": payload.prompt_lab_url,
        "low_confidence": payload.low_confidence,
        "summary_url": (
            _summary_url(
                request_id=payload.request_id,
                query_signature_hash=payload.query_signature_hash,
                query_text=payload.query_text,
                template_key="summary-default",
                template_version="v1",
            )
            if payload.all_results
            else None
        ),
    }
    context.update(_build_pagination_context(request, payload.page_obj))
    return context


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
    path = request.path
    if path.endswith("/search/results"):
        path = "/"
    return f"{path}?{query.urlencode()}"


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


def _summary_url(
    *,
    request_id: str,
    query_signature_hash: str,
    query_text: str,
    template_key: str,
    template_version: str,
) -> str:
    query = urlencode(
        {
            "request_id": request_id,
            "query_signature_hash": query_signature_hash,
            "query_text": query_text,
            "summary_template_key": template_key,
            "summary_template_version": template_version,
        }
    )
    return f"/search/summary?{query}"


def _query_signature_hash(*, cleaned_data: dict[str, object], suppress: bool) -> str:
    payload = {
        "query_text": _to_optional_str(cleaned_data.get("query_text")),
        "expansion_mode": _to_expansion_mode(cleaned_data.get("expansion_mode")),
        "category": _to_optional_str(cleaned_data.get("category")),
        "include_keyword": _to_optional_str(cleaned_data.get("include_keyword")),
        "exclude_keyword": _to_optional_str(cleaned_data.get("exclude_keyword")),
        "sort": _to_sort_mode(cleaned_data.get("sort")),
        "min_price_eur": _to_optional_float(cleaned_data.get("min_price_eur")),
        "max_price_eur": _to_optional_float(cleaned_data.get("max_price_eur")),
        "exact_dimensions": bool(cleaned_data.get("exact_dimensions")),
        "width_exact_cm": _to_optional_float(cleaned_data.get("width_exact_cm")),
        "width_min_cm": _to_optional_float(cleaned_data.get("width_min_cm")),
        "width_max_cm": _to_optional_float(cleaned_data.get("width_max_cm")),
        "depth_exact_cm": _to_optional_float(cleaned_data.get("depth_exact_cm")),
        "depth_min_cm": _to_optional_float(cleaned_data.get("depth_min_cm")),
        "depth_max_cm": _to_optional_float(cleaned_data.get("depth_max_cm")),
        "height_exact_cm": _to_optional_float(cleaned_data.get("height_exact_cm")),
        "height_min_cm": _to_optional_float(cleaned_data.get("height_min_cm")),
        "height_max_cm": _to_optional_float(cleaned_data.get("height_max_cm")),
        "show_without_expansion": suppress,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _query_cache_config_hash() -> str:
    settings = get_settings()
    payload = {
        "embedding_model": settings.gemini_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "rerank_backend": settings.rerank_backend,
        "rerank_enabled": settings.rerank_enabled,
        "rerank_model_name": settings.rerank_model_name,
        "rerank_candidate_limit": settings.rerank_candidate_limit,
        "result_limit": max(200, settings.default_query_limit),
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resultset_hash(products: tuple[SummaryCandidateProduct, ...]) -> str:
    serialized = json.dumps(
        [
            {
                "canonical_product_key": product.canonical_product_key,
                "item_name": product.item_name,
            }
            for product in products
        ],
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _summary_config_hash(*, template_key: str, template_version: str) -> str:
    settings = get_settings()
    payload = {
        "template_key": template_key,
        "template_version": template_version,
        "model_name": settings.gemini_generation_model,
        "schema_version": 2,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _summary_cache_key(
    *, query_signature_hash: str, resultset_hash: str, summary_config_hash: str
) -> str:
    seed = f"{query_signature_hash}:{resultset_hash}:{summary_config_hash}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _sanitize_summary_items(
    *, parsed: SearchSummaryResponse, products: tuple[SummaryCandidateProduct, ...]
) -> SearchSummaryResponse | None:
    """Normalize cached summary items to known candidate IDs and names only."""

    candidate_name_by_key = {
        product.canonical_product_key: product.item_name for product in products
    }
    items = []
    for item in parsed.items:
        name = candidate_name_by_key.get(item.canonical_product_key)
        if name is None:
            continue
        items.append(
            {
                "canonical_product_key": item.canonical_product_key,
                "item_name": name,
                "why": item.why,
            }
        )
    if not items:
        return None
    return SearchSummaryResponse(summary=parsed.summary, items=items)


def _load_cached_summary(
    *,
    repository: Phase3Repository,
    summary_json: str | None,
    summary_cache_key: str,
    request_id: str,
    query_signature_hash: str,
    resultset_hash: str,
    summary_config_hash: str,
    products: tuple[SummaryCandidateProduct, ...],
) -> SearchSummaryResponse | None:
    """Load cached summary, sanitize candidate IDs/names, and re-cache if normalized."""

    if summary_json is None:
        return None
    try:
        parsed = SearchSummaryResponse.model_validate_json(summary_json)
    except ValidationError:
        return None
    sanitized = _sanitize_summary_items(parsed=parsed, products=products)
    if sanitized is None:
        return None
    if sanitized.model_dump_json() != summary_json:
        repository.upsert_summary_cache(
            summary_cache_key=summary_cache_key,
            request_id=request_id,
            query_signature_hash=query_signature_hash,
            resultset_hash=resultset_hash,
            summary_config_hash=summary_config_hash,
            summary_json=sanitized.model_dump_json(),
            ttl_hours=24,
        )
    return sanitized


def _conversation_url(conversation_id: str) -> str:
    return f"/conversations/{conversation_id}"


def _parse_reason_tags(raw: object) -> tuple[str, ...]:
    text = _to_optional_str(raw)
    if text is None:
        return ()
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _prompt_lab_redirect(request: HttpRequest) -> str:
    request_id = _to_optional_str(request.POST.get("request_id")) or ""
    query_text = _to_optional_str(request.POST.get("query_text")) or ""
    return _prompt_lab_url(request_id=request_id, query_text=query_text)


def _split_changed_and_unchanged(
    rows: tuple[ResultDiffRow, ...],
) -> tuple[tuple[ResultDiffRow, ...], int]:
    changed_rows = tuple(row for row in rows if row.rank_delta != 0)
    unchanged_count = len(rows) - len(changed_rows)
    return changed_rows, unchanged_count
