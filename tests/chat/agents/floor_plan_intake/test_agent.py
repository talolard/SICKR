from __future__ import annotations

from typing import cast

from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.floor_plan_intake.agent import (
    TOOL_NAMES,
    build_floor_plan_intake_agent,
)


def test_floor_plan_intake_agent_loads_prompt_instructions() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "floor-plan intake specialist" in instructions
    assert "render_floor_plan" in instructions


def test_floor_plan_intake_agent_registers_floor_plan_tools() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    floor_plan_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(floor_plan_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)
