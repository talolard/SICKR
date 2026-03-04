"""Application URL routes for semantic search and shortlist actions."""

from __future__ import annotations

from django.urls import path

from tal_maria_ikea.web.views import (
    ConversationView,
    ItemFeedbackView,
    PromptLabView,
    RerankDiffView,
    SearchResultsPartialView,
    SearchSummaryPartialView,
    SearchView,
    ShortlistAddView,
    ShortlistRemoveView,
    StatsView,
    TurnFeedbackView,
)

app_name = "web"

urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("search/results", SearchResultsPartialView.as_view(), name="search-results"),
    path("search/summary", SearchSummaryPartialView.as_view(), name="search-summary"),
    path("prompt-lab", PromptLabView.as_view(), name="prompt-lab"),
    path("conversations/<str:conversation_id>", ConversationView.as_view(), name="conversation"),
    path("stats", StatsView.as_view(), name="stats"),
    path("feedback/turn", TurnFeedbackView.as_view(), name="feedback-turn"),
    path("feedback/item", ItemFeedbackView.as_view(), name="feedback-item"),
    path("analysis/rerank-diff/<str:request_id>", RerankDiffView.as_view(), name="rerank-diff"),
    path("shortlist/add", ShortlistAddView.as_view(), name="shortlist-add"),
    path("shortlist/remove", ShortlistRemoveView.as_view(), name="shortlist-remove"),
]
