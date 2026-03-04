"""Django admin registrations for Phase 3 config models."""

from __future__ import annotations

from typing import ClassVar

from django.contrib import admin
from django.forms import ModelForm

from tal_maria_ikea.web.models import (
    ExpansionPolicyConfig,
    FeedbackReasonTag,
    PromptVariantSet,
    SystemPromptTemplate,
)

admin.site.site_header = "IKEA Search Admin"
admin.site.site_title = "IKEA Search Admin"
admin.site.index_title = "Feature Configuration"


class SystemPromptTemplateAdminForm(ModelForm):
    """Clarify prompt template fields for operators."""

    class Meta:
        """Model form metadata for admin rendering."""

        model = SystemPromptTemplate
        fields = "__all__"
        help_texts: ClassVar[dict[str, str]] = {
            "key": (
                "Stable template family key (for example: summary, query-expansion, "
                "follow-up). Use the same key across versions."
            ),
            "version": (
                "Template revision identifier (for example: v1, v2, experiment-a). "
                "Combined with key it must be unique."
            ),
            "title": "Human-readable label shown in admin lists.",
            "template_text": (
                "Prompt body. Must include {{ user_query }} so runtime can inject user text."
            ),
            "is_active": "Only active templates should be used by runtime selection.",
        }


class PromptVariantSetAdminForm(ModelForm):
    """Clarify Prompt Lab variant set fields for operators."""

    class Meta:
        """Model form metadata for admin rendering."""

        model = PromptVariantSet
        fields = "__all__"
        help_texts: ClassVar[dict[str, str]] = {
            "name": "Stable internal key for this variant set (slug).",
            "title": "Display name shown to operators.",
            "description": "When this set should be used and what it compares.",
            "max_variants": "Maximum templates to run in one Prompt Lab comparison.",
            "templates": "Templates included in this Prompt Lab set.",
            "is_active": "Only active sets should be available for comparisons.",
        }


class FeedbackReasonTagAdminForm(ModelForm):
    """Clarify feedback reason tag fields."""

    class Meta:
        """Model form metadata for admin rendering."""

        model = FeedbackReasonTag
        fields = "__all__"
        help_texts: ClassVar[dict[str, str]] = {
            "scope": "What is being rated: assistant turn text or an individual item.",
            "polarity": "Which thumb direction this reason belongs to.",
            "label": "Stable machine label used in stored telemetry.",
            "title": "Human-readable option shown in UI.",
            "is_active": "Inactive tags stay in history but are hidden from new feedback.",
        }


class ExpansionPolicyConfigAdminForm(ModelForm):
    """Clarify query-expansion policy fields for operators."""

    class Meta:
        """Model form metadata for admin rendering."""

        model = ExpansionPolicyConfig
        fields = "__all__"
        help_texts: ClassVar[dict[str, str]] = {
            "key": "Stable policy key (for example: default, strict, recall-heavy).",
            "title": "Human-readable policy name for operators.",
            "auto_mode_enabled": "Whether expansion mode=auto can apply this policy.",
            "min_confidence": "Minimum confidence required before applying expansion.",
            "min_constraint_signals": (
                "Minimum number of constraint signals (price, size, category, etc.) "
                "before auto mode applies expansion."
            ),
            "notes": "Operational notes and rollout context.",
            "is_active": "Inactive policies are ignored by runtime.",
        }


@admin.register(SystemPromptTemplate)
class SystemPromptTemplateAdmin(admin.ModelAdmin):
    """Admin settings for system prompt templates."""

    form = SystemPromptTemplateAdminForm
    list_display = (  # pyrefly: ignore[bad-override]
        "key",
        "version",
        "title",
        "is_active",
        "updated_at",
    )
    list_display_links = ("key", "version")
    list_filter = ("key", "is_active")
    search_fields = ("key", "version", "title")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Template Identity",
            {
                "description": (
                    "Prompt template definitions used by Search summaries, rerank explanations, "
                    "and conversation follow-ups."
                ),
                "fields": ("key", "version", "title", "is_active"),
            },
        ),
        (
            "Template Body",
            {
                "fields": ("template_text",),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    ordering = ("key", "version")


@admin.register(PromptVariantSet)
class PromptVariantSetAdmin(admin.ModelAdmin):
    """Admin settings for prompt variant sets."""

    form = PromptVariantSetAdminForm
    list_display = (  # pyrefly: ignore[bad-override]
        "name",
        "title",
        "max_variants",
        "is_active",
        "updated_at",
    )
    list_display_links = ("name", "title")
    list_filter = ("is_active",)
    search_fields = ("name", "title")
    filter_horizontal = ("templates",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Prompt Lab Identity",
            {
                "description": (
                    "Defines a reusable set of prompt templates for side-by-side compare."
                ),
                "fields": ("name", "title", "description", "is_active"),
            },
        ),
        (
            "Comparison Limits",
            {
                "fields": ("max_variants",),
            },
        ),
        (
            "Included Templates",
            {
                "fields": ("templates",),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    ordering = ("name",)


@admin.register(FeedbackReasonTag)
class FeedbackReasonTagAdmin(admin.ModelAdmin):
    """Admin settings for reason tags."""

    form = FeedbackReasonTagAdminForm
    list_display = (  # pyrefly: ignore[bad-override]
        "scope",
        "polarity",
        "label",
        "title",
        "is_active",
    )
    list_display_links = ("label", "title")
    list_filter = ("scope", "polarity", "is_active")
    search_fields = ("label", "title")
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "Tag Definition",
            {
                "description": (
                    "Reason tags shown in feedback forms. Scope + polarity + label must be unique."
                ),
                "fields": ("scope", "polarity", "label", "title", "is_active"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at",),
            },
        ),
    )
    ordering = ("scope", "polarity", "label")


@admin.register(ExpansionPolicyConfig)
class ExpansionPolicyConfigAdmin(admin.ModelAdmin):
    """Admin settings for expansion policy controls."""

    form = ExpansionPolicyConfigAdminForm
    list_display = (  # pyrefly: ignore[bad-override]
        "key",
        "title",
        "auto_mode_enabled",
        "min_confidence",
        "is_active",
    )
    list_display_links = ("key", "title")
    list_filter = ("is_active", "auto_mode_enabled")
    search_fields = ("key", "title")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Policy Identity",
            {
                "description": (
                    "Controls when query expansion auto-mode is allowed and how strict "
                    "it should be."
                ),
                "fields": ("key", "title", "is_active"),
            },
        ),
        (
            "Runtime Thresholds",
            {
                "fields": ("auto_mode_enabled", "min_confidence", "min_constraint_signals"),
            },
        ),
        (
            "Operator Notes",
            {
                "fields": ("notes",),
            },
        ),
        (
            "Audit",
            {
                "fields": ("updated_at",),
            },
        ),
    )
    ordering = ("key",)
