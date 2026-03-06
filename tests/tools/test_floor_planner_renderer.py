from __future__ import annotations

from pathlib import Path

from ikea_agent.tools.floorplanner.models import BaselineFloorPlanScene
from ikea_agent.tools.floorplanner.renderer import FloorPlannerRenderer


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
                    {
                        "wall_id": "w4",
                        "start_cm": {"x_cm": 0.0, "y_cm": 260.0},
                        "end_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    },
                ],
                "doors": [
                    {
                        "opening_id": "d1",
                        "label": "entrance door",
                        "start_cm": {"x_cm": 0.0, "y_cm": 230.0},
                        "end_cm": {"x_cm": 0.0, "y_cm": 260.0},
                    }
                ],
                "windows": [
                    {
                        "opening_id": "win1",
                        "label": "kitchen window",
                        "start_cm": {"x_cm": 340.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": 340.0, "y_cm": 190.0},
                    }
                ],
            },
            "placements": [
                {
                    "placement_id": "desk",
                    "name": "Desk",
                    "kind": "generic",
                    "position_cm": {"x_cm": 220.0, "y_cm": 0.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 75.0},
                },
                {
                    "placement_id": "shelf1",
                    "name": "Shelf",
                    "kind": "shelf",
                    "position_cm": {"x_cm": 220.0, "y_cm": 0.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 20.0, "z_cm": 2.0},
                    "z_cm": 100.0,
                    "wall_mounted": True,
                },
            ],
        }
    )


def test_renderer_writes_stable_svg_and_png(tmp_path: Path) -> None:
    result = FloorPlannerRenderer().render(_scene(), tmp_path)

    assert result.output_svg.exists()
    assert result.output_png.exists()
    assert result.output_svg.name == "floor_plan.svg"
    assert result.output_png.name == "floor_plan.png"
    assert result.output_svg.stat().st_size > 0
    assert result.output_png.stat().st_size > 0


def test_renderer_svg_contains_expected_layers(tmp_path: Path) -> None:
    result = FloorPlannerRenderer().render(_scene(), tmp_path)

    svg_text = result.output_svg.read_text(encoding="utf-8")
    assert 'id="architecture"' in svg_text
    assert 'id="placements"' in svg_text
    assert 'id="elevation"' in svg_text
    assert 'id="legend"' in svg_text
    assert "entrance door" in svg_text
    assert "kitchen window" in svg_text
