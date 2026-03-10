from __future__ import annotations

import asyncio
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from ikea_agent.chat.subagents.floor_plan_intake.agent import FloorPlannerSubgraphAgent
from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDecision,
    FloorPlanIntakeDeps,
    FloorPlanIntakeInput,
    FloorPlanIntakeState,
)
from ikea_agent.tools.floorplanner.models import (
    ArchitectureScene,
    BaselineFloorPlanScene,
    FloorPlanRenderOutput,
    Point2DCm,
    RoomDimensionsCm,
    WallSegmentCm,
)


def _scene() -> BaselineFloorPlanScene:
    return BaselineFloorPlanScene(
        architecture=ArchitectureScene(
            dimensions_cm=RoomDimensionsCm(length_x_cm=300.0, depth_y_cm=400.0, height_z_cm=260.0),
            walls=[
                WallSegmentCm(
                    wall_id="w1",
                    start_cm=Point2DCm(x_cm=0.0, y_cm=0.0),
                    end_cm=Point2DCm(x_cm=300.0, y_cm=0.0),
                ),
                WallSegmentCm(
                    wall_id="w2",
                    start_cm=Point2DCm(x_cm=300.0, y_cm=0.0),
                    end_cm=Point2DCm(x_cm=300.0, y_cm=400.0),
                ),
            ],
        )
    )


def _render_output(scene_revision: int) -> FloorPlanRenderOutput:
    return FloorPlanRenderOutput(
        caption="draft",
        scene_revision=scene_revision,
        scene_level="baseline",
        output_svg_path="draft.svg",
        output_png_path="draft.png",
        warnings=[],
        legend_items=[],
        scale_major_step_cm=50,
        scene=_scene(),
    )


async def _fake_decider(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
) -> FloorPlanIntakeDecision:
    _ = (state, payload)
    return FloorPlanIntakeDecision(
        next_action="ask_dimensions",
        assistant_message="Please share rough dimensions.",
    )


def test_floor_planner_subgraph_agent_metadata_contains_prompt_graph_and_tools() -> None:
    metadata = FloorPlannerSubgraphAgent.build_metadata()

    assert metadata["name"] == "floor_plan_intake"
    assert "stateDiagram-v2" in metadata["mermaid"]
    assert "Floor Plan Intake Subagent Prompt" in metadata["prompt_markdown"]
    assert metadata["tools"] == ["decide_floor_plan_intake_step", "render_floor_plan_draft"]


def test_floor_planner_subgraph_agent_builds_agent_with_prompt_instructions() -> None:
    agent = FloorPlannerSubgraphAgent.build_agent()

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "Floor Plan Intake Subagent Prompt" in instructions


def test_floor_planner_subgraph_agent_run_one_turn_with_mocked_deps(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _build_mock_deps(*, model_name: str) -> FloorPlanIntakeDeps:
        _ = model_name
        return FloorPlanIntakeDeps(
            output_dir=tmp_path,
            floor_plan_renderer=lambda **_: _render_output(1),
            intake_decider=_fake_decider,
        )

    def _patched_build_deps(
        _subgraph_cls: type[FloorPlannerSubgraphAgent],
        *,
        model_name: str,
    ) -> FloorPlanIntakeDeps:
        return _build_mock_deps(model_name=model_name)

    monkeypatch.setattr(
        FloorPlannerSubgraphAgent,
        "build_deps",
        classmethod(_patched_build_deps),
    )

    output = asyncio.run(
        FloorPlannerSubgraphAgent.run_one_turn(
            user_message="hello",
            model_name="test-model",
        )
    )

    assert (
        FloorPlannerSubgraphAgent.extract_assistant_message(output)
        == "Please share rough dimensions."
    )
