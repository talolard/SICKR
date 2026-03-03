"""Django app config for semantic search UI."""

from __future__ import annotations

from django.apps import AppConfig


class WebAppConfig(AppConfig):
    """Register local web app components."""

    name = "tal_maria_ikea.web"
    verbose_name = "IKEA Semantic Search"
