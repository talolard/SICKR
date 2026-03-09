from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

import ikea_agent.chat.subagents.floor_plan_intake.graph as graph_module
from ikea_agent.chat.subagents.floor_plan_intake.graph import (
    build_floor_plan_intake_graph,
    run_floor_plan_intake,
    run_from_raw_input,
)
from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDeps,
    FloorPlanIntakeInput,
    FloorPlanIntakeOutcome,
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
                WallSegmentCm(
                    wall_id="w3",
                    start_cm=Point2DCm(x_cm=300.0, y_cm=400.0),
                    end_cm=Point2DCm(x_cm=0.0, y_cm=400.0),
                ),
                WallSegmentCm(
                    wall_id="w4",
                    start_cm=Point2DCm(x_cm=0.0, y_cm=400.0),
                    end_cm=Point2DCm(x_cm=0.0, y_cm=0.0),
                ),
            ],
        )
    )


def _render_output(scene_revision: int) -> FloorPlanRenderOutput:
    scene = _scene()
    return FloorPlanRenderOutput(
        caption="draft",
        scene_revision=scene_revision,
        scene_level="baseline",
        output_svg_path="draft.svg",
        output_png_path="draft.png",
        warnings=[],
        legend_items=[],
        scale_major_step_cm=50,
        scene=scene,
    )


def test_graph_returns_unsupported_image_exit_when_images_are_present(tmp_path: Path) -> None:
    graph = build_floor_plan_intake_graph()

    def _renderer(**_: object) -> FloorPlanRenderOutput:
        return _render_output(1)

    result = asyncio.run(
        graph.run(
            state=FloorPlanIntakeState(),
            deps=FloorPlanIntakeDeps(output_dir=tmp_path, floor_plan_renderer=_renderer),
            inputs=FloorPlanIntakeInput(user_message="Here are images", images=["a.png"]),
        )
    )

    assert result.status == "unsupported_image"
    assert result.should_exit is True
    assert "do not support picture parsing yet" in result.assistant_message


def test_graph_renders_after_move_on_with_dimensions_and_orientation(tmp_path: Path) -> None:
    graph = build_floor_plan_intake_graph()

    def _renderer(**_: object) -> FloorPlanRenderOutput:
        return _render_output(1)

    result = asyncio.run(
        graph.run(
            state=FloorPlanIntakeState(),
            deps=FloorPlanIntakeDeps(output_dir=tmp_path, floor_plan_renderer=_renderer),
            inputs=FloorPlanIntakeInput(
                user_message=(
                    "I have a 300 by 400 room, ceiling is 260 cm, with my back to the door "
                    "there is a window on the left. let's move on"
                )
            ),
        )
    )

    assert result.status == "rendered_draft"
    assert result.render_output is not None
    assert result.render_output.scene_revision == 1


def test_run_floor_plan_intake_executes_with_renderer(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(graph_module, "render_floor_plan_draft", lambda **_: _render_output(1))

    payload = FloorPlanIntakeInput(
        user_message=(
            "I have a 300 by 400 room, ceiling is 260 cm, with my back to the door "
            "window is on the right, let's move on"
        )
    )
    result = asyncio.run(run_floor_plan_intake(payload, output_dir=tmp_path))

    assert result.status == "rendered_draft"
    assert result.render_output is not None


def test_run_from_raw_input_accepts_plain_text(monkeypatch: MonkeyPatch) -> None:
    async def _fake_run(
        payload: FloorPlanIntakeInput,
        *,
        output_dir: Path = graph_module.DEFAULT_OUTPUT_DIR,
    ) -> FloorPlanIntakeOutcome:
        _ = output_dir
        return FloorPlanIntakeOutcome(
            status="ask_user",
            should_exit=False,
            assistant_message=payload.user_message,
            scene_revision=0,
        )

    monkeypatch.setattr(graph_module, "run_floor_plan_intake", _fake_run)

    output = asyncio.run(run_from_raw_input("room is 300 by 400"))

    assert output["status"] == "ask_user"
    assert output["assistant_message"] == "room is 300 by 400"


def test_run_floor_plan_intake_fails_when_prompt_is_missing(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(graph_module, "PROMPT_PATH", tmp_path / "missing_prompt.md")
    payload = FloorPlanIntakeInput(user_message="300 by 400")

    with pytest.raises(FileNotFoundError):
        _ = asyncio.run(run_floor_plan_intake(payload, output_dir=tmp_path))
