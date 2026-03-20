"""Model construction helpers for agent runtime.

Live model requests now follow the application defaults, but tests remain
deterministic because the backend suite applies Pydantic AI's request gate
globally in `tests/conftest.py`. Missing API keys still degrade to `TestModel`
so local runs fail clearly instead of making partial network attempts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.config import AppSettings


def build_deterministic_function_model(
    *,
    output_text: str,
    model_name: str,
) -> FunctionModel:
    """Build a deterministic streaming model for smoke and integration tests."""

    async def _function(
        _messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=output_text)])

    async def _stream(
        _messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> AsyncIterator[str]:
        yield output_text

    return FunctionModel(
        function=_function,
        stream_function=_stream,
        model_name=model_name,
    )


def build_google_or_test_model(
    *,
    settings: AppSettings,
    model_name: str,
    google_model_settings: GoogleModelSettings,
    disabled_reason: str,
) -> FunctionModel | GoogleModel | TestModel:
    """Build the configured live model or a deterministic local fallback."""

    deterministic_response = settings.deterministic_model_response_text
    if deterministic_response:
        return build_deterministic_function_model(
            output_text=deterministic_response,
            model_name=f"deterministic-{model_name}",
        )

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
