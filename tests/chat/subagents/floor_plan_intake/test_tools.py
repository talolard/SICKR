from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ikea_agent.chat.subagents.floor_plan_intake.tools.floorplan_render import (
    render_floor_plan_draft,
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


def test_render_floor_plan_draft_calls_repo_tool(tmp_path: Path) -> None:
    scene = _scene()
    expected = FloorPlanRenderOutput(
        caption="ok",
        scene_revision=1,
        scene_level="baseline",
        output_svg_path="a.svg",
        output_png_path="a.png",
        warnings=[],
        legend_items=[],
        scale_major_step_cm=50,
        scene=scene,
    )

    with patch(
        "ikea_agent.chat.subagents.floor_plan_intake.tools.floorplan_render.render_floor_plan",
        return_value=(scene, expected, None),
    ) as mocked:
        output = render_floor_plan_draft(
            scene=scene,
            scene_revision=1,
            current_scene=None,
            output_dir=tmp_path,
            include_image_bytes=False,
        )

    assert output == expected
    assert mocked.call_count == 1
