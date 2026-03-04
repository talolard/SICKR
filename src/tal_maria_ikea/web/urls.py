"""Application URL routes for semantic search and shortlist actions."""

from __future__ import annotations

from django.urls import path

from tal_maria_ikea.web.views import (
    ConversationView,
    PromptLabView,
    RerankDiffView,
    SearchView,
    ShortlistAddView,
    ShortlistRemoveView,
    StatsView,
)

app_name = "web"

urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("prompt-lab", PromptLabView.as_view(), name="prompt-lab"),
    path("conversations/<str:conversation_id>", ConversationView.as_view(), name="conversation"),
    path("stats", StatsView.as_view(), name="stats"),
    path("analysis/rerank-diff/<str:request_id>", RerankDiffView.as_view(), name="rerank-diff"),
    path("shortlist/add", ShortlistAddView.as_view(), name="shortlist-add"),
    path("shortlist/remove", ShortlistRemoveView.as_view(), name="shortlist-remove"),
]
