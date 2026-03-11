"""Model construction helpers for agent runtime.

The default repo experience should be deterministic and safe: local runs and CI
must not accidentally trigger paid network calls just because a user opened the UI.
Real model-backed runs are opt-in via settings.
"""

from __future__ import annotations

from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.config import AppSettings


def build_google_or_test_model(
    *,
    settings: AppSettings,
    model_name: str,
    google_model_settings: GoogleModelSettings,
    disabled_reason: str,
) -> GoogleModel | TestModel:
    """Build a Google model when enabled, otherwise a deterministic local TestModel."""

    if not settings.allow_model_requests:
        return TestModel(call_tools=[], custom_output_text=disabled_reason)

    api_key = settings.gemini_api_key
    if not api_key:
        return TestModel(
            call_tools=[],
            custom_output_text=(
                "Model requests enabled but no API key is configured. "
                "Set GEMINI_API_KEY or GOOGLE_API_KEY (and ensure ALLOW_MODEL_REQUESTS=1)."
            ),
        )

    return GoogleModel(
        model_name,
        settings=google_model_settings,
        provider=GoogleProvider(api_key=api_key),
    )
