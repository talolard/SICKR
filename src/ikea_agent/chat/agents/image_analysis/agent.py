"""Pydantic-ai image-analysis agent."""

from __future__ import annotations

import os
from pathlib import Path

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.agents.common import AgentPrompt
from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.image_analysis.toolset import TOOL_NAMES, build_image_analysis_toolset
from ikea_agent.config import get_settings

AGENT_NAME = "image_analysis"
DESCRIPTION = "Analyze uploaded room photos with object detection, depth, and segmentation."
PROMPT_PATH = Path(__file__).with_name("prompt.md")
PROMPT = AgentPrompt(PROMPT_PATH)
NOTES = "Image-analysis focused agent with attachment-driven tool calls."


def resolve_model_name(*, explicit_model: str | None = None) -> str:
    """Resolve model using explicit override, agent config, then global default."""

    if explicit_model:
        return explicit_model
    settings = get_settings()
    configured_model = settings.agent_model(AGENT_NAME)
    if configured_model:
        return configured_model
    return settings.gemini_generation_model


def build_image_analysis_agent(
    *, explicit_model: str | None = None
) -> Agent[ImageAnalysisAgentDeps, str]:
    """Build image-analysis agent."""

    settings = get_settings()
    google_model_settings = GoogleModelSettings(
        google_thinking_config=ThinkingConfigDict(
            include_thoughts=True,
            thinking_level=ThinkingLevel.HIGH,
        )
    )
    model = GoogleModel(
        resolve_model_name(explicit_model=explicit_model),
        settings=google_model_settings,
        provider=GoogleProvider(api_key=settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")),
    )
    return Agent[ImageAnalysisAgentDeps, str](
        model=model,
        deps_type=ImageAnalysisAgentDeps,
        output_type=str,
        name="agent_image_analysis",
        instructions=PROMPT.instruction_text(),
        toolsets=[build_image_analysis_toolset()],
    )


__all__ = [
    "AGENT_NAME",
    "DESCRIPTION",
    "NOTES",
    "PROMPT",
    "PROMPT_PATH",
    "TOOL_NAMES",
    "build_image_analysis_agent",
    "resolve_model_name",
]
