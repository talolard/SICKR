from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
from ikea_agent.tools.floorplanner.models import BaselineFloorPlanScene, scene_to_summary


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_duckdb_engine(str(tmp_path / "floor_plan_repository_test.duckdb"))
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _scene(name: str) -> BaselineFloorPlanScene:
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
            "placements": [
                {
                    "placement_id": f"{name}-wardrobe",
                    "name": "Wardrobe",
                    "position_cm": {"x_cm": 20.0, "y_cm": 30.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 200.0},
                }
            ],
        }
    )


def test_floor_plan_repository_persists_revision_history_across_instances(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    first_repository = FloorPlanRepository(session_factory)

    first = _scene("first")
    second = _scene("second")

    saved_first = first_repository.save_revision(
        thread_id="thread-floor",
        scene=first,
        summary=scene_to_summary(first),
        svg_asset_id="asset-svg-1",
        png_asset_id="asset-png-1",
    )
    saved_second = first_repository.save_revision(
        thread_id="thread-floor",
        scene=second,
        summary=scene_to_summary(second),
        svg_asset_id="asset-svg-2",
        png_asset_id="asset-png-2",
    )

    restarted_repository = FloorPlanRepository(session_factory)
    latest = restarted_repository.get_latest_revision(thread_id="thread-floor")

    assert saved_first.revision == 1
    assert saved_second.revision == 2
    assert latest is not None
    assert latest.revision == 2
    assert latest.svg_asset_id is None
    assert latest.scene.placements[0].placement_id == "second-wardrobe"


def test_floor_plan_repository_confirms_latest_revision(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = FloorPlanRepository(session_factory)
    scene = _scene("confirmed")

    repository.save_revision(
        thread_id="thread-floor-confirm",
        scene=scene,
        summary=scene_to_summary(scene),
        svg_asset_id="asset-svg-confirm",
        png_asset_id="asset-png-confirm",
    )

    confirmed = repository.confirm_revision(
        thread_id="thread-floor-confirm",
        revision=None,
        run_id=None,
        confirmation_note="User confirmed this layout.",
    )

    assert confirmed is not None
    assert confirmed.revision == 1
    assert confirmed.confirmed_at is not None
    assert confirmed.confirmation_note == "User confirmed this layout."
