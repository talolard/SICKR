from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikea_agent.tools.floorplanner.models import (
    BaselineFloorPlanScene,
    FloorPlanRenderRequest,
    SceneChangeSet,
    apply_changes,
    scene_to_summary,
)
from ikea_agent.tools.floorplanner.yaml_codec import dump_scene_yaml, parse_scene_yaml


def _scene_payload() -> dict[str, object]:
    return {
        "scene_level": "baseline",
        "architecture": {
            "dimensions_cm": {
                "length_x_cm": 340.0,
                "depth_y_cm": 260.0,
                "height_z_cm": 260.0,
            },
            "walls": [
                {
                    "wall_id": "bottom",
                    "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "end_cm": {"x_cm": 340.0, "y_cm": 0.0},
                },
                {
                    "wall_id": "right",
                    "start_cm": {"x_cm": 340.0, "y_cm": 0.0},
                    "end_cm": {"x_cm": 340.0, "y_cm": 260.0},
                },
                {
                    "wall_id": "top",
                    "start_cm": {"x_cm": 340.0, "y_cm": 260.0},
                    "end_cm": {"x_cm": 0.0, "y_cm": 260.0},
                },
                {
                    "wall_id": "left",
                    "start_cm": {"x_cm": 0.0, "y_cm": 260.0},
                    "end_cm": {"x_cm": 0.0, "y_cm": 0.0},
                },
            ],
        },
        "placements": [
            {
                "placement_id": "desk",
                "name": "Desk",
                "kind": "generic",
                "position_cm": {"x_cm": 220.0, "y_cm": 0.0},
                "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 75.0},
            }
        ],
    }


def test_baseline_scene_accepts_valid_payload() -> None:
    scene = BaselineFloorPlanScene.model_validate(_scene_payload())

    assert scene.scene_level == "baseline"
    assert len(scene.architecture.walls) == 4
    assert len(scene.placements) == 1


def test_render_request_requires_scene_or_changes() -> None:
    with pytest.raises(ValidationError, match="At least one of `scene` or `changes`"):
        FloorPlanRenderRequest.model_validate({})


def test_apply_changes_upserts_and_removes_placements() -> None:
    scene = BaselineFloorPlanScene.model_validate(_scene_payload())

    changes = SceneChangeSet.model_validate(
        {
            "upsert_placements": [
                {
                    "placement_id": "desk",
                    "name": "Desk Moved",
                    "kind": "generic",
                    "position_cm": {"x_cm": 200.0, "y_cm": 10.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 75.0},
                },
                {
                    "placement_id": "bed",
                    "name": "Bed",
                    "kind": "generic",
                    "position_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 200.0, "z_cm": 140.0},
                },
            ]
        }
    )

    changed = apply_changes(scene, changes)

    assert len(changed.placements) == 2
    moved = next(item for item in changed.placements if item.placement_id == "desk")
    assert moved.name == "Desk Moved"


def test_yaml_parse_and_dump_round_trip_keeps_core_dimensions() -> None:
    yaml_text = """
room:
  dimensions:
    length_x: 340
    depth_y: 260
    height_z: 260
  walls:
    bottom: { axis: "x", at_y: 0, from_x: 0, to_x: 340 }
    top: { axis: "x", at_y: 260, from_x: 0, to_x: 340 }
    left: { axis: "y", at_x: 0, from_y: 0, to_y: 260 }
    right: { axis: "y", at_x: 340, from_y: 0, to_y: 260 }
furniture:
  - id: "desk"
    name: "Desk"
    dims: { x: 100, y: 60, z: 75 }
    pos: { x: 220, y: 0 }
"""

    scene = parse_scene_yaml(yaml_text)
    dumped = dump_scene_yaml(scene)
    reparsed = parse_scene_yaml(dumped)

    assert reparsed.architecture.dimensions_cm.length_x_cm == 340.0
    assert reparsed.architecture.dimensions_cm.depth_y_cm == 260.0
    assert len(reparsed.placements) == 1


def test_architecture_rejects_door_not_on_wall() -> None:
    payload = _scene_payload()
    architecture = payload["architecture"]
    assert isinstance(architecture, dict)
    architecture["doors"] = [
        {
            "opening_id": "floating-door",
            "start_cm": {"x_cm": 50.0, "y_cm": 50.0},
            "end_cm": {"x_cm": 80.0, "y_cm": 50.0},
        }
    ]

    with pytest.raises(ValidationError, match="must lie on a wall segment"):
        BaselineFloorPlanScene.model_validate(payload)


def test_architecture_accepts_door_optional_vertical_range() -> None:
    payload = _scene_payload()
    architecture = payload["architecture"]
    assert isinstance(architecture, dict)
    architecture["doors"] = [
        {
            "opening_id": "entry-door",
            "start_cm": {"x_cm": 0.0, "y_cm": 30.0},
            "end_cm": {"x_cm": 0.0, "y_cm": 90.0},
            "z_min_cm": 0.0,
            "z_max_cm": 210.0,
        }
    ]

    scene = BaselineFloorPlanScene.model_validate(payload)
    assert len(scene.architecture.doors) == 1
    assert scene.architecture.doors[0].z_max_cm == pytest.approx(210.0)


def test_architecture_rejects_door_invalid_vertical_range() -> None:
    payload = _scene_payload()
    architecture = payload["architecture"]
    assert isinstance(architecture, dict)
    architecture["doors"] = [
        {
            "opening_id": "entry-door",
            "start_cm": {"x_cm": 0.0, "y_cm": 30.0},
            "end_cm": {"x_cm": 0.0, "y_cm": 90.0},
            "z_min_cm": 120.0,
            "z_max_cm": 80.0,
        }
    ]

    with pytest.raises(ValidationError, match="z_max_cm must be greater than or equal to z_min_cm"):
        BaselineFloorPlanScene.model_validate(payload)


def test_scene_summary_prefers_labels_for_openings_and_walls() -> None:
    payload = _scene_payload()
    architecture = payload["architecture"]
    assert isinstance(architecture, dict)
    walls = architecture["walls"]
    assert isinstance(walls, list)
    walls[0]["label"] = "bottom wall"
    architecture["doors"] = [
        {
            "opening_id": "main-door",
            "label": "entrance door",
            "start_cm": {"x_cm": 0.0, "y_cm": 20.0},
            "end_cm": {"x_cm": 0.0, "y_cm": 80.0},
        }
    ]
    architecture["windows"] = [
        {
            "opening_id": "win-1",
            "label": "kitchen window",
            "start_cm": {"x_cm": 340.0, "y_cm": 80.0},
            "end_cm": {"x_cm": 340.0, "y_cm": 180.0},
        }
    ]
    scene = BaselineFloorPlanScene.model_validate(payload)
    summary = scene_to_summary(scene)

    assert "bottom wall" in summary["wall_labels"]
    assert summary["door_labels"] == ["entrance door"]
    assert summary["window_labels"] == ["kitchen window"]
