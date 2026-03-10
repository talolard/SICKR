"""Model-backed decision helper for floor-plan intake routing."""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDecision,
    FloorPlanIntakeInput,
    FloorPlanIntakeState,
)
from ikea_agent.config import get_settings


def _build_default_decider_instructions() -> str:
    return (
        "You are a floor-plan intake routing specialist. "
        "Given current intake state and latest user turn, choose exactly one next_action: "
        "complete, ask_dimensions, ask_orientation, ask_constraints, render. "
        "Return concise assistant_message in the same collaborative tone. "
        "Do not claim to parse images. If images are mentioned in payload context "
        "and parsing is unsupported, "
        "focus on text-only continuation guidance. "
        "Extract any newly stated room dimensions, wall height, room type, "
        "orientation coverage, and fixed constraints. "
        "Keep room_type stable once established unless user explicitly corrects room type. "
        "Do not treat movable furniture mentions (for example 'kitchen table') as room_type "
        "switch signals. "
        "If room_type is ambiguous, keep the previous room_type and ask a clarifying question. "
        "If user asks to move on or provide corrections after a prior draft, choose render."
    )


def _build_decider_instructions(*, prompt_instructions: str) -> str:
    return (
        f"{prompt_instructions.strip()}\n\n"
        "Routing contract:\n"
        "- Choose exactly one next_action from: complete, ask_dimensions, ask_orientation, "
        "ask_constraints, render.\n"
        "- Return concise assistant_message in the same collaborative tone.\n"
        "- Extract any newly stated room dimensions, wall height, room type, orientation coverage, "
        "and fixed constraints.\n"
        "- Keep room_type stable once established unless user explicitly corrects room type.\n"
        "- Do not treat movable furniture mentions (for example 'kitchen table') as room_type "
        "switch signals.\n"
        "- If room_type is ambiguous, keep previous room_type and ask a clarifying question.\n"
        "- If user asks to move on or provide corrections after a prior draft, choose render.\n"
    )


@lru_cache(maxsize=16)
def _build_decider_agent(
    *,
    instructions: str,
    model_name: str,
) -> Agent[None, FloorPlanIntakeDecision]:
    settings = get_settings()
    model = GoogleModel(
        model_name,
        settings=GoogleModelSettings(
            google_thinking_config=ThinkingConfigDict(include_thoughts=False),
        ),
        provider=GoogleProvider(api_key=settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")),
    )
    return Agent[None, FloorPlanIntakeDecision](
        model=model,
        deps_type=type(None),
        instructions=instructions,
        output_type=FloorPlanIntakeDecision,
    )


def _build_decider_prompt(*, state: FloorPlanIntakeState, payload: FloorPlanIntakeInput) -> str:
    state_payload = {
        "room_type": state.room_type,
        "length_cm": state.length_cm,
        "depth_cm": state.depth_cm,
        "wall_height_cm": state.wall_height_cm,
        "orientation_context_collected": state.orientation_context_collected,
        "fixed_constraints": state.fixed_constraints,
        "question_rounds": state.question_rounds,
        "scene_revision": state.scene_revision,
        "has_last_render": state.last_render is not None,
    }
    input_payload = payload.model_dump(mode="json")
    return (
        "Return a FloorPlanIntakeDecision JSON object.\n"
        f"Current state:\n{json.dumps(state_payload, ensure_ascii=True)}\n"
        f"Latest input:\n{json.dumps(input_payload, ensure_ascii=True)}\n"
    )


async def decide_floor_plan_intake_step(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
) -> FloorPlanIntakeDecision:
    """Use the configured model to decide intake routing for one turn."""

    settings = get_settings()
    instructions = _build_default_decider_instructions()
    agent = _build_decider_agent(
        instructions=instructions,
        model_name=settings.gemini_generation_model,
    )
    prompt = _build_decider_prompt(state=state, payload=payload)
    result = await agent.run(prompt)
    return result.output


def build_floor_plan_intake_decider(
    *,
    prompt_instructions: str,
    model_name: str | None = None,
) -> Callable[..., Awaitable[FloorPlanIntakeDecision]]:
    """Create a decider callable bound to prompt-driven instructions and model."""

    settings = get_settings()
    resolved_model_name = model_name or settings.gemini_generation_model
    instructions = _build_decider_instructions(prompt_instructions=prompt_instructions)
    agent = _build_decider_agent(
        instructions=instructions,
        model_name=resolved_model_name,
    )

    async def _decide(
        *,
        state: FloorPlanIntakeState,
        payload: FloorPlanIntakeInput,
    ) -> FloorPlanIntakeDecision:
        prompt = _build_decider_prompt(state=state, payload=payload)
        result = await agent.run(prompt)
        return result.output

    return _decide
