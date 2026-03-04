"""Django admin registrations for Phase 3 config models."""

from __future__ import annotations

from django.contrib import admin

from tal_maria_ikea.web.models import (
    ExpansionPolicyConfig,
    FeedbackReasonTag,
    PromptVariantSet,
    SystemPromptTemplate,
)


@admin.register(SystemPromptTemplate)
class SystemPromptTemplateAdmin(admin.ModelAdmin):
    """Admin settings for system prompt templates."""

    list_display = (  # pyrefly: ignore[bad-override]
        "key",
        "version",
        "title",
        "is_active",
        "updated_at",
    )
    list_filter = ("key", "is_active")
    search_fields = ("key", "version", "title")
    ordering = ("key", "version")


@admin.register(PromptVariantSet)
class PromptVariantSetAdmin(admin.ModelAdmin):
    """Admin settings for prompt variant sets."""

    list_display = (  # pyrefly: ignore[bad-override]
        "name",
        "title",
        "max_variants",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "title")
    filter_horizontal = ("templates",)
    ordering = ("name",)


@admin.register(FeedbackReasonTag)
class FeedbackReasonTagAdmin(admin.ModelAdmin):
    """Admin settings for reason tags."""

    list_display = (  # pyrefly: ignore[bad-override]
        "scope",
        "polarity",
        "label",
        "title",
        "is_active",
    )
    list_filter = ("scope", "polarity", "is_active")
    search_fields = ("label", "title")
    ordering = ("scope", "polarity", "label")


@admin.register(ExpansionPolicyConfig)
class ExpansionPolicyConfigAdmin(admin.ModelAdmin):
    """Admin settings for expansion policy controls."""

    list_display = (  # pyrefly: ignore[bad-override]
        "key",
        "title",
        "auto_mode_enabled",
        "min_confidence",
        "is_active",
    )
    list_filter = ("is_active", "auto_mode_enabled")
    search_fields = ("key", "title")
    ordering = ("key",)
