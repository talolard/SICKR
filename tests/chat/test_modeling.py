from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.google import GoogleModelSettings

from ikea_agent.chat.modeling import build_google_or_test_model
from ikea_agent.config import AppSettings


def test_build_google_or_test_model_uses_deterministic_function_model_when_configured() -> None:
    settings = AppSettings(
        GOOGLE_API_KEY="test-google-api-key",
        DETERMINISTIC_MODEL_RESPONSE_TEXT="Deterministic smoke response from the local test model.",
    )

    model = build_google_or_test_model(
        settings=settings,
        model_name="gemini-test",
        google_model_settings=GoogleModelSettings(),
        disabled_reason="disabled",
    )

    assert isinstance(model, FunctionModel)
    agent = Agent(model=model, output_type=str)
    result = agent.run_sync("hello")

    assert result.output == "Deterministic smoke response from the local test model."
