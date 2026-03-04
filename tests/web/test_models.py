from __future__ import annotations

import os

import django
import pytest
from django.core.exceptions import ValidationError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tal_maria_ikea.web.project.settings")
django.setup()

from tal_maria_ikea.web.models import (  # noqa: E402
    ExpansionPolicyConfig,
    FeedbackReasonTag,
    PromptVariantSet,
    SystemPromptTemplate,
)


def test_system_prompt_template_requires_user_query_placeholder() -> None:
    template = SystemPromptTemplate(
        key="summary",
        version="v1",
        title="Summary v1",
        template_text="No query placeholder here.",
    )

    with pytest.raises(ValidationError):
        template.full_clean(validate_unique=False, validate_constraints=False)


def test_prompt_variant_set_defaults_are_admin_safe() -> None:
    variant_set = PromptVariantSet(name="default-set", title="Default")

    variant_set.full_clean(
        exclude=["templates"],
        validate_unique=False,
        validate_constraints=False,
    )

    assert variant_set.max_variants == 5
    assert variant_set.is_active is True


def test_feedback_reason_tag_choice_validation() -> None:
    reason = FeedbackReasonTag(
        scope="bad-scope",
        polarity="up",
        label="helpful",
        title="Helpful",
    )

    with pytest.raises(ValidationError):
        reason.full_clean(validate_unique=False, validate_constraints=False)


def test_expansion_policy_confidence_bounds_validation() -> None:
    policy = ExpansionPolicyConfig(
        key="default",
        title="Default policy",
        min_confidence=1.2,
    )

    with pytest.raises(ValidationError):
        policy.full_clean(validate_unique=False, validate_constraints=False)
