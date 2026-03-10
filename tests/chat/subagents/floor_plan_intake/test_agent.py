from __future__ import annotations

from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    TOOL_NAMES,
    build_floor_plan_intake_agent,
)


def test_floor_plan_intake_agent_loads_prompt_instructions() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "Floor Plan Intake Subagent Prompt" in instructions
    assert "render_floor_plan" in instructions


def test_floor_plan_intake_agent_registers_floor_plan_tools() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    registered_tools = set(agent._function_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)
