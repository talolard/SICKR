"""Django config models for Phase 3 prompt and feedback controls."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SystemPromptTemplate(models.Model):
    """Versioned system-prompt template editable from Django admin."""

    key = models.SlugField(max_length=80)
    version = models.CharField(max_length=40)
    title = models.CharField(max_length=120)
    template_text = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Database constraints and stable ordering."""

        constraints = (
            models.UniqueConstraint(fields=["key", "version"], name="uniq_prompt_key_version"),
        )
        ordering = ("key", "version")

    def clean(self) -> None:
        """Ensure templates include explicit user-query context interpolation."""

        super().clean()
        template_text = str(self.template_text or "")
        if "{{ user_query }}" not in template_text:
            raise ValidationError("Template must include `{{ user_query }}` placeholder.")

    def __str__(self) -> str:
        """Return a concise admin display identifier."""

        return f"{self.key}:{self.version}"


class PromptVariantSet(models.Model):
    """Named set of prompt templates used for side-by-side variant comparison."""

    name = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    max_variants = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    templates = models.ManyToManyField(
        SystemPromptTemplate, related_name="variant_sets", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Default ordering for admin/query display."""

        ordering = ("name",)

    def __str__(self) -> str:
        """Return a concise admin display identifier."""

        return str(self.name)


class FeedbackReasonTag(models.Model):
    """Feedback reason tags scoped by rating target and polarity."""

    scope = models.CharField(
        max_length=20,
        choices=(
            ("turn", "Turn"),
            ("item", "Item"),
        ),
    )
    polarity = models.CharField(
        max_length=10,
        choices=(
            ("up", "Thumbs up"),
            ("down", "Thumbs down"),
        ),
    )
    label = models.SlugField(max_length=80)
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Database constraints and stable ordering."""

        constraints = (
            models.UniqueConstraint(
                fields=["scope", "polarity", "label"],
                name="uniq_feedback_reason_scope_polarity_label",
            ),
        )
        ordering = ("scope", "polarity", "label")

    def __str__(self) -> str:
        """Return a concise admin display identifier."""

        return f"{self.scope}:{self.polarity}:{self.label}"


class ExpansionPolicyConfig(models.Model):
    """Heuristic controls for query-expansion auto mode."""

    key = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    auto_mode_enabled = models.BooleanField(default=True)
    min_confidence = models.FloatField(
        default=0.70,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    min_constraint_signals = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Default ordering for admin/query display."""

        ordering = ("key",)

    def __str__(self) -> str:
        """Return a concise admin display identifier."""

        return str(self.key)
