"""Application URL routes for semantic search and shortlist actions."""

from __future__ import annotations

from django.urls import path

from tal_maria_ikea.web.views import SearchView, ShortlistAddView, ShortlistRemoveView

app_name = "web"

urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("shortlist/add", ShortlistAddView.as_view(), name="shortlist-add"),
    path("shortlist/remove", ShortlistRemoveView.as_view(), name="shortlist-remove"),
]
