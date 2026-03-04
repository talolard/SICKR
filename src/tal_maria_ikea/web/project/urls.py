"""Project URL conf."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tal_maria_ikea.web.urls", namespace="web")),
]
