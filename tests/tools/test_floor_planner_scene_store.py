from __future__ import annotations

from ikea_agent.tools.floorplanner.models import BaselineFloorPlanScene
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore


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


def test_scene_store_isolated_by_session() -> None:
    store = FloorPlanSceneStore()

    a = store.set("a", _scene())
    b = store.set("b", _scene())

    assert a.revision == 1
    assert b.revision == 1
    assert store.get("a") is not None
    assert store.get("b") is not None


def test_scene_store_increments_revision() -> None:
    store = FloorPlanSceneStore()

    first = store.set("session-1", _scene())
    second = store.set("session-1", _scene())

    assert first.revision == 1
    assert second.revision == 2


def test_scene_store_accepts_explicit_revision() -> None:
    store = FloorPlanSceneStore()

    snapshot = store.set_with_revision("session-1", _scene(), revision=7)

    assert snapshot.revision == 7
