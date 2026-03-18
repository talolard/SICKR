"""Pydantic-ai search agent."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModelSettings, ThinkingConfigDict

from ikea_agent.chat.agents.common import AgentPrompt
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import (
    TOOL_NAMES,
    SearchToolsetServices,
    build_search_toolset,
)
from ikea_agent.chat.agents.shared import build_preference_instruction
from ikea_agent.chat.modeling import build_google_or_test_model
from ikea_agent.config import get_settings

AGENT_NAME = "search"
DESCRIPTION = "Find IKEA products using retrieval, reranking, and diversity-aware selection."
PROMPT_PATH = Path(__file__).with_name("prompt.md")
PROMPT = AgentPrompt(PROMPT_PATH)
NOTES = "Search-focused agent with retrieval and 3D snapshot context tools."
PREFERENCE_INSTRUCTION: Callable[[RunContext[SearchAgentDeps]], str] = cast(
    "Callable[[RunContext[SearchAgentDeps]], str]", build_preference_instruction()
)


def resolve_model_name(*, explicit_model: str | None = None) -> str:
    """Resolve model using explicit override, agent config, then global default."""

    if explicit_model:
        return explicit_model
    settings = get_settings()
    configured_model = settings.agent_model(AGENT_NAME)
    if configured_model:
        return configured_model
    return settings.gemini_generation_model


def build_search_agent(
    *,
    explicit_model: str | None = None,
    toolset_services: SearchToolsetServices | None = None,
) -> Agent[SearchAgentDeps, str]:
    """Build search agent."""

    settings = get_settings()
    google_model_settings = GoogleModelSettings(
        google_thinking_config=ThinkingConfigDict(
            include_thoughts=True,
            thinking_level=ThinkingLevel.HIGH,
        )
    )
    model = build_google_or_test_model(
        settings=settings,
        model_name=resolve_model_name(explicit_model=explicit_model),
        google_model_settings=google_model_settings,
        disabled_reason=(
            "Live model requests are disabled. "
            "Set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY/GOOGLE_API_KEY for real responses."
        ),
    )
    return Agent[SearchAgentDeps, str](
        model=model,
        deps_type=SearchAgentDeps,
        instructions=[PROMPT.instruction_text(), PREFERENCE_INSTRUCTION],
        output_type=str,
        name="agent_search",
        toolsets=[build_search_toolset(toolset_services)],
    )


__all__ = [
    "AGENT_NAME",
    "DESCRIPTION",
    "NOTES",
    "PROMPT",
    "PROMPT_PATH",
    "TOOL_NAMES",
    "build_search_agent",
    "resolve_model_name",
]
