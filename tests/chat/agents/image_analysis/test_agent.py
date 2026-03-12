from __future__ import annotations

from typing import cast

from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.image_analysis.agent import (
    TOOL_NAMES,
    build_image_analysis_agent,
)


def test_image_analysis_agent_loads_prompt_instructions() -> None:
    agent = build_image_analysis_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "room-image analysis specialist" in instructions
    assert "get_room_detail_details_from_photo" in instructions


def test_image_analysis_agent_registers_room_detail_tool() -> None:
    agent = build_image_analysis_agent(explicit_model="gemini-2.0-flash")

    image_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(image_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)
