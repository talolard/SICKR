"""Project URL conf."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("tal_maria_ikea.web.urls", namespace="web")),
]
