"""Plain pydantic-ai subagent for floor-plan intake."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.subagents.common import SubagentPrompt
from ikea_agent.chat.tools.floor_plan_tools import register_floor_plan_tools
from ikea_agent.config import get_settings

SUBAGENT_NAME = "floor_plan_intake"
DESCRIPTION = "Collect initial room architecture and render iterative floor-plan drafts."
PROMPT_PATH = Path(__file__).with_name("prompt.md")
PROMPT = SubagentPrompt(PROMPT_PATH)
TOOL_NAMES: tuple[str, ...] = (
    "render_floor_plan",
    "load_floor_plan_scene_yaml",
    "export_floor_plan_scene_yaml",
    "confirm_floor_plan_revision",
)
NOTES = (
    "Runs an iterative intake loop directly in a pydantic-ai agent and uses the shared "
    "`render_floor_plan` tool contract so CopilotKit can render floor-plan outputs."
)


def resolve_model_name(*, explicit_model: str | None = None) -> str:
    """Resolve model using explicit override, subagent config, then global default."""

    if explicit_model:
        return explicit_model
    settings = get_settings()
    configured_model = settings.subagent_model(SUBAGENT_NAME)
    if configured_model:
        return configured_model
    return settings.gemini_generation_model


def build_floor_plan_intake_agent(
    *, explicit_model: str | None = None
) -> Agent[ChatAgentDeps, str]:
    """Build the floor-plan intake subagent as a regular pydantic-ai agent."""

    settings = get_settings()
    model = GoogleModel(
        resolve_model_name(explicit_model=explicit_model),
        settings=GoogleModelSettings(
            google_thinking_config=ThinkingConfigDict(include_thoughts=False),
        ),
        provider=GoogleProvider(api_key=settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")),
    )
    agent = Agent[ChatAgentDeps, str](
        model=model,
        deps_type=ChatAgentDeps,
        output_type=str,
        name="subagent_floor_plan_intake",
        instructions=PROMPT.instruction_text(),
    )
    register_floor_plan_tools(agent)
    return agent


__all__ = [
    "DESCRIPTION",
    "NOTES",
    "PROMPT",
    "PROMPT_PATH",
    "SUBAGENT_NAME",
    "TOOL_NAMES",
    "build_floor_plan_intake_agent",
    "resolve_model_name",
]
