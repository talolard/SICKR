"""Plain pydantic-ai agent for floor-plan intake."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModelSettings, ThinkingConfigDict

from ikea_agent.chat.agents.common import AgentPrompt
from ikea_agent.chat.agents.floor_plan_intake.deps import FloorPlanIntakeDeps
from ikea_agent.chat.agents.floor_plan_intake.toolset import (
    TOOL_NAMES,
    build_floor_plan_intake_toolset,
)
from ikea_agent.chat.modeling import build_google_or_test_model
from ikea_agent.config import get_settings

AGENT_NAME = "floor_plan_intake"
DESCRIPTION = "Collect initial room architecture and render iterative floor-plan drafts."
PROMPT_PATH = Path(__file__).with_name("prompt.md")
PROMPT = AgentPrompt(PROMPT_PATH)
NOTES = (
    "Runs an iterative intake loop directly in a pydantic-ai agent and uses the shared "
    "`render_floor_plan` tool contract so CopilotKit can render floor-plan outputs."
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


def build_floor_plan_intake_agent(
    *, explicit_model: str | None = None
) -> Agent[FloorPlanIntakeDeps, str]:
    """Build the floor-plan intake agent as a regular pydantic-ai agent."""

    settings = get_settings()
    model = build_google_or_test_model(
        settings=settings,
        model_name=resolve_model_name(explicit_model=explicit_model),
        google_model_settings=GoogleModelSettings(
            google_thinking_config=ThinkingConfigDict(include_thoughts=False),
        ),
        disabled_reason=(
            "Live model requests are disabled. "
            "Set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY/GOOGLE_API_KEY for real responses."
        ),
    )
    return Agent[FloorPlanIntakeDeps, str](
        model=model,
        deps_type=FloorPlanIntakeDeps,
        output_type=str,
        name="agent_floor_plan_intake",
        instructions=PROMPT.instruction_text(),
        toolsets=[build_floor_plan_intake_toolset()],
    )


__all__ = [
    "AGENT_NAME",
    "DESCRIPTION",
    "NOTES",
    "PROMPT",
    "PROMPT_PATH",
    "TOOL_NAMES",
    "build_floor_plan_intake_agent",
    "resolve_model_name",
]
