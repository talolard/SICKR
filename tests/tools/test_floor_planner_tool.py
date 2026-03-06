from __future__ import annotations

from pathlib import Path

from pydantic_ai import ToolReturn
from pydantic_ai.messages import BinaryContent

from ikea_agent.tools.floorplanner.models import BaselineFloorPlanScene, FloorPlanRenderRequest
from ikea_agent.tools.floorplanner.tool import render_floor_plan


def _scene() -> BaselineFloorPlanScene:
    return BaselineFloorPlanScene.model_validate(
        {
            "scene_level": "baseline",
            "architecture": {
                "dimensions_cm": {
                    "length_x_cm": 340.0,
                    "depth_y_cm": 260.0,
                    "height_z_cm": 260.0,
                },
                "walls": [
                    {
                        "wall_id": "w1",
                        "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": 340.0, "y_cm": 0.0},
                    },
                    {
                        "wall_id": "w2",
                        "start_cm": {"x_cm": 340.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": 340.0, "y_cm": 260.0},
                    },
                    {
                        "wall_id": "w3",
                        "start_cm": {"x_cm": 340.0, "y_cm": 260.0},
                        "end_cm": {"x_cm": 0.0, "y_cm": 260.0},
                    },
                ],
            },
            "placements": [],
        }
    )


def test_render_floor_plan_returns_scene_and_output(tmp_path: Path) -> None:
    request = FloorPlanRenderRequest(scene=_scene(), include_image_bytes=False)

    scene, output, tool_return = render_floor_plan(
        request,
        scene_revision=1,
        current_scene=None,
        output_dir=tmp_path,
    )

    assert scene.scene_level == "baseline"
    assert output.scene_revision == 1
    assert output.output_svg_path == str(tmp_path / "floor_plan.svg")
    assert output.output_png_path == str(tmp_path / "floor_plan.png")
    assert tool_return is None


def test_render_floor_plan_can_return_tool_return(tmp_path: Path) -> None:
    request = FloorPlanRenderRequest(scene=_scene(), include_image_bytes=True)

    _scene_obj, _output, tool_return = render_floor_plan(
        request,
        scene_revision=2,
        current_scene=None,
        output_dir=tmp_path,
    )

    assert isinstance(tool_return, ToolReturn)
    assert tool_return.metadata is not None
    assert tool_return.metadata["scene_revision"] == 2
    assert isinstance(tool_return.content, list)
    assert len(tool_return.content) == 1
    assert isinstance(tool_return.content[0], BinaryContent)


def test_render_floor_plan_applies_incremental_changes(tmp_path: Path) -> None:
    base_scene = _scene()
    request = FloorPlanRenderRequest(
        changes={
            "upsert_placements": [
                {
                    "placement_id": "desk",
                    "name": "Desk",
                    "kind": "generic",
                    "position_cm": {"x_cm": 220.0, "y_cm": 0.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 75.0},
                }
            ]
        },
        include_image_bytes=False,
    )

    scene, output, _tool_return = render_floor_plan(
        request,
        scene_revision=3,
        current_scene=base_scene,
        output_dir=tmp_path,
    )

    assert len(scene.placements) == 1
    assert output.scene_revision == 3
