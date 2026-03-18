from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pydantic_ai import ToolReturn
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.floor_plan_intake.agent import (
    TOOL_NAMES,
    build_floor_plan_intake_agent,
)
from ikea_agent.chat.agents.floor_plan_intake.toolset import (
    FloorPlanIntakeToolsetServices,
    FloorPlanRenderer,
)
from ikea_agent.tools.floorplanner.models import FloorPlanRenderOutput, FloorPlanScene


@dataclass(frozen=True, slots=True)
class _RenderFloorPlanStub:
    def __call__(
        self,
        request: object,
        *,
        scene_revision: int,
        current_scene: FloorPlanScene | None,
    ) -> tuple[FloorPlanScene, FloorPlanRenderOutput, ToolReturn | None]:
        _ = (request, scene_revision, current_scene)
        raise RuntimeError("stub should not be invoked in builder-only test")


def test_floor_plan_intake_agent_loads_prompt_instructions() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions).lower()
    assert "floor-plan intake specialist" in instructions
    assert "render_floor_plan" in instructions


def test_floor_plan_intake_agent_registers_floor_plan_tools() -> None:
    agent = build_floor_plan_intake_agent(explicit_model="gemini-2.0-flash")

    floor_plan_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(floor_plan_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)


def test_floor_plan_intake_agent_accepts_injected_toolset_services() -> None:
    services = FloorPlanIntakeToolsetServices(
        render_floor_plan=cast("FloorPlanRenderer", _RenderFloorPlanStub()),
        get_floor_plan_repository=lambda _runtime: None,
    )

    agent = build_floor_plan_intake_agent(
        explicit_model="gemini-2.0-flash",
        toolset_services=services,
    )

    floor_plan_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    assert set(TOOL_NAMES).issubset(floor_plan_toolset.tools)
