from __future__ import annotations

from pathlib import Path

from ikea_agent.tools.floorplanner.models import FloorPlanRequest
from ikea_agent.tools.floorplanner.renderer import FloorPlannerRenderer


def _complex_room_payload() -> dict[str, object]:
    return {
        "elements": [
            {
                "type": "wall",
                "name": "w1",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                "length_cm": 340.0,
                "thickness_cm": 10.0,
            },
            {
                "type": "wall",
                "name": "w2",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 0.0},
                "length_cm": 190.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 90.0,
            },
            {
                "type": "wall",
                "name": "w3",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 190.0},
                "length_cm": 20.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 180.0,
            },
            {
                "type": "wall",
                "name": "w4",
                "anchor_point_cm": {"x_cm": 320.0, "y_cm": 190.0},
                "length_cm": 70.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 90.0,
            },
            {
                "type": "wall",
                "name": "w5",
                "anchor_point_cm": {"x_cm": 320.0, "y_cm": 260.0},
                "length_cm": 320.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 180.0,
                "color": "#e87830",
            },
            {
                "type": "wall",
                "name": "w6",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 260.0},
                "length_cm": 260.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": -90.0,
            },
            {
                "type": "door",
                "name": "left_door",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                "doorway_width_cm": 30.0,
                "door_width_cm": 28.0,
                "thickness_cm": 5.0,
                "orientation_angle_deg": 90.0,
                "to_the_right": True,
            },
            {
                "type": "window",
                "name": "right_window",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 10.0},
                "length_cm": 160.0,
                "overall_thickness_cm": 10.0,
                "single_line_thickness_cm": 3.0,
                "orientation_angle_deg": 90.0,
            },
        ],
    }


def _hallway_payload() -> dict[str, object]:
    return {
        "elements": [
            {
                "type": "wall",
                "name": "h1",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                "length_cm": 700.0,
                "thickness_cm": 10.0,
            },
            {
                "type": "wall",
                "name": "h2",
                "anchor_point_cm": {"x_cm": 700.0, "y_cm": 0.0},
                "length_cm": 250.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 90.0,
            },
            {
                "type": "wall",
                "name": "h3",
                "anchor_point_cm": {"x_cm": 700.0, "y_cm": 250.0},
                "length_cm": 700.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": 180.0,
            },
            {
                "type": "wall",
                "name": "h4",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 250.0},
                "length_cm": 250.0,
                "thickness_cm": 10.0,
                "orientation_angle_deg": -90.0,
            },
            {
                "type": "door",
                "name": "d1",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 85.0},
                "doorway_width_cm": 90.0,
                "door_width_cm": 80.0,
                "thickness_cm": 5.0,
                "orientation_angle_deg": -90.0,
            },
            {
                "type": "door",
                "name": "d2",
                "anchor_point_cm": {"x_cm": 700.0, "y_cm": 80.0},
                "doorway_width_cm": 90.0,
                "door_width_cm": 80.0,
                "thickness_cm": 5.0,
                "orientation_angle_deg": 90.0,
            },
            {
                "type": "door",
                "name": "d3",
                "anchor_point_cm": {"x_cm": 200.0, "y_cm": 0.0},
                "doorway_width_cm": 80.0,
                "door_width_cm": 70.0,
                "thickness_cm": 5.0,
            },
            {
                "type": "door",
                "name": "d4",
                "anchor_point_cm": {"x_cm": 320.0, "y_cm": 250.0},
                "doorway_width_cm": 80.0,
                "door_width_cm": 70.0,
                "thickness_cm": 5.0,
                "orientation_angle_deg": 180.0,
            },
        ],
    }


def test_renderer_writes_png_for_complex_room(tmp_path: Path) -> None:
    request = FloorPlanRequest.model_validate(_complex_room_payload())

    result = FloorPlannerRenderer().render(request, tmp_path)

    assert result.output_png.exists()
    assert result.output_png.name == "floor_plan.png"
    assert result.output_png.stat().st_size > 0
    assert result.wall_count == 6
    assert result.window_count == 1


def test_renderer_writes_png_for_hallway(tmp_path: Path) -> None:
    request = FloorPlanRequest.model_validate(_hallway_payload())

    result = FloorPlannerRenderer().render(request, tmp_path)

    assert result.output_png.exists()
    assert result.output_png.name == "floor_plan.png"
    assert result.output_png.stat().st_size > 0
    assert result.door_count == 4
