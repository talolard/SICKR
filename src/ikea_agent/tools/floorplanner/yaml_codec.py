"""YAML import/export helpers for floor-plan scene contracts.

Runtime tools should accept typed Pydantic objects. These helpers provide controlled
interop with human-authored YAML files.
"""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import TypeAdapter

from ikea_agent.tools.floorplanner.models import (
    ArchitectureScene,
    BaselineFloorPlanScene,
    DetailedFloorPlanScene,
    DoorOpeningCm,
    FloorPlanScene,
    FurniturePlacementCm,
    LightFixture,
    Point2DCm,
    RoomDimensionsCm,
    SceneFixture,
    SocketFixture,
    WallSegmentCm,
    WindowOpeningCm,
)

_SCENE_ADAPTER = TypeAdapter(FloorPlanScene)
_MIN_WALL_SEGMENTS = 3


def _to_float(value: object, *, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return default


def parse_scene_yaml(yaml_text: str, *, scene_level: str = "detailed") -> FloorPlanScene:
    """Parse YAML into a typed scene model.

    The parser supports the existing room YAML shape used in local experiments.
    Missing sections fall back to safe defaults where possible.
    """

    payload = yaml.safe_load(yaml_text)
    if not isinstance(payload, dict):
        raise TypeError("YAML payload must decode to a mapping")

    room = payload.get("room") or {}
    dimensions = room.get("dimensions") or {}

    scene_dimensions = RoomDimensionsCm(
        length_x_cm=_to_float(dimensions.get("length_x", dimensions.get("length_x_cm", 0.0))),
        depth_y_cm=_to_float(dimensions.get("depth_y", dimensions.get("depth_y_cm", 0.0))),
        height_z_cm=_to_float(dimensions.get("height_z", dimensions.get("height_z_cm", 0.0))),
    )

    walls = _extract_walls(room, scene_dimensions)
    doors, windows = _extract_openings(room, scene_dimensions)

    architecture = ArchitectureScene(
        dimensions_cm=scene_dimensions,
        walls=walls,
        doors=doors,
        windows=windows,
    )
    placements = _extract_furniture(payload)
    fixtures = _extract_fixtures(payload)

    if scene_level == "baseline":
        scene: FloorPlanScene = BaselineFloorPlanScene(
            architecture=architecture,
            placements=placements,
        )
    else:
        scene = DetailedFloorPlanScene(
            architecture=architecture,
            placements=placements,
            fixtures=fixtures,
        )

    return _SCENE_ADAPTER.validate_python(scene.model_dump(mode="python"))


def dump_scene_yaml(scene: FloorPlanScene) -> str:
    """Serialize typed scene objects back to a concise YAML structure."""

    room_yaml: dict[str, Any] = {
        "dimensions": {
            "length_x": scene.architecture.dimensions_cm.length_x_cm,
            "depth_y": scene.architecture.dimensions_cm.depth_y_cm,
            "height_z": scene.architecture.dimensions_cm.height_z_cm,
        },
        "walls": {
            "segments": [
                {
                    "id": wall.wall_id,
                    "from": [wall.start_cm.x_cm, wall.start_cm.y_cm],
                    "to": [wall.end_cm.x_cm, wall.end_cm.y_cm],
                    "thickness_cm": wall.thickness_cm,
                    "color": wall.color,
                }
                for wall in scene.architecture.walls
            ]
        },
        "features": {
            "doors": [
                {
                    "id": door.opening_id,
                    "from": [door.start_cm.x_cm, door.start_cm.y_cm],
                    "to": [door.end_cm.x_cm, door.end_cm.y_cm],
                    "panel_length": door.panel_length_cm,
                    "opens_towards": door.opens_towards,
                }
                for door in scene.architecture.doors
            ],
            "windows": [
                {
                    "id": window.opening_id,
                    "from": [window.start_cm.x_cm, window.start_cm.y_cm],
                    "to": [window.end_cm.x_cm, window.end_cm.y_cm],
                    "z_range": [window.z_min_cm, window.z_max_cm],
                    "panel_count": window.panel_count,
                    "frame_cm": window.frame_cm,
                }
                for window in scene.architecture.windows
            ],
        },
    }

    furniture_yaml: list[dict[str, Any]] = [
        {
            "id": placement.placement_id,
            "name": placement.name,
            "kind": placement.kind,
            "pos": {
                "x": placement.position_cm.x_cm,
                "y": placement.position_cm.y_cm,
                "z": placement.z_cm,
            },
            "dims": {
                "x": placement.size_cm.x_cm,
                "y": placement.size_cm.y_cm,
                "z": placement.size_cm.z_cm,
            },
            "color": placement.color,
            "wall_mounted": placement.wall_mounted,
            "stacked_on": placement.stacked_on_placement_id,
            "label": placement.label,
            "notes": placement.notes,
        }
        for placement in scene.placements
    ]

    payload: dict[str, Any] = {
        "room": room_yaml,
        "furniture": furniture_yaml,
    }

    if isinstance(scene, DetailedFloorPlanScene) and scene.fixtures:
        payload["fixtures"] = [
            {
                "id": fixture.fixture_id,
                "kind": fixture.fixture_kind,
                "x": fixture.x_cm,
                "y": fixture.y_cm,
                "z": fixture.z_cm,
                "label": fixture.label,
            }
            for fixture in scene.fixtures
        ]

    return yaml.safe_dump(payload, sort_keys=False)


def _extract_walls(room: dict[str, Any], dimensions: RoomDimensionsCm) -> list[WallSegmentCm]:
    walls_payload = room.get("walls") or {}

    if isinstance(walls_payload.get("segments"), list):
        return [
            WallSegmentCm(
                wall_id=str(segment.get("id", f"wall_{index}")),
                start_cm=Point2DCm(
                    x_cm=float(segment["from"][0]),
                    y_cm=float(segment["from"][1]),
                ),
                end_cm=Point2DCm(
                    x_cm=float(segment["to"][0]),
                    y_cm=float(segment["to"][1]),
                ),
                thickness_cm=float(segment.get("thickness_cm", 10.0)),
                color=segment.get("color"),
            )
            for index, segment in enumerate(walls_payload["segments"])
        ]

    walls: list[WallSegmentCm] = []
    bottom = walls_payload.get("bottom") or {}
    top = walls_payload.get("top") or {}
    left = walls_payload.get("left") or {}
    right = walls_payload.get("right") or {}

    if bottom:
        walls.append(
            WallSegmentCm(
                wall_id="bottom",
                start_cm=Point2DCm(
                    x_cm=float(bottom.get("from_x", 0.0)), y_cm=float(bottom.get("at_y", 0.0))
                ),
                end_cm=Point2DCm(
                    x_cm=float(bottom.get("to_x", dimensions.length_x_cm)),
                    y_cm=float(bottom.get("at_y", 0.0)),
                ),
                color=bottom.get("color"),
            )
        )
    if right:
        walls.append(
            WallSegmentCm(
                wall_id="right",
                start_cm=Point2DCm(
                    x_cm=float(right.get("at_x", dimensions.length_x_cm)),
                    y_cm=float(right.get("from_y", 0.0)),
                ),
                end_cm=Point2DCm(
                    x_cm=float(right.get("at_x", dimensions.length_x_cm)),
                    y_cm=float(right.get("to_y", dimensions.depth_y_cm)),
                ),
                color=right.get("color"),
            )
        )
    if top:
        walls.append(
            WallSegmentCm(
                wall_id="top",
                start_cm=Point2DCm(
                    x_cm=float(top.get("from_x", 0.0)),
                    y_cm=float(top.get("at_y", dimensions.depth_y_cm)),
                ),
                end_cm=Point2DCm(
                    x_cm=float(top.get("to_x", dimensions.length_x_cm)),
                    y_cm=float(top.get("at_y", dimensions.depth_y_cm)),
                ),
                color=top.get("color"),
            )
        )
    if left:
        walls.append(
            WallSegmentCm(
                wall_id="left",
                start_cm=Point2DCm(
                    x_cm=float(left.get("at_x", 0.0)), y_cm=float(left.get("from_y", 0.0))
                ),
                end_cm=Point2DCm(
                    x_cm=float(left.get("at_x", 0.0)),
                    y_cm=float(left.get("to_y", dimensions.depth_y_cm)),
                ),
                color=left.get("color"),
            )
        )

    inset = walls_payload.get("corner_inset") or {}
    segments = inset.get("segments") or []
    for index, segment in enumerate(segments):
        walls.append(
            WallSegmentCm(
                wall_id=f"corner_inset_{index}",
                start_cm=Point2DCm(x_cm=float(segment["from"][0]), y_cm=float(segment["from"][1])),
                end_cm=Point2DCm(x_cm=float(segment["to"][0]), y_cm=float(segment["to"][1])),
            )
        )

    if len(walls) < _MIN_WALL_SEGMENTS:
        walls = [
            WallSegmentCm(
                wall_id="fallback_bottom",
                start_cm=Point2DCm(x_cm=0.0, y_cm=0.0),
                end_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=0.0),
            ),
            WallSegmentCm(
                wall_id="fallback_right",
                start_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=0.0),
                end_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=dimensions.depth_y_cm),
            ),
            WallSegmentCm(
                wall_id="fallback_top",
                start_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=dimensions.depth_y_cm),
                end_cm=Point2DCm(x_cm=0.0, y_cm=dimensions.depth_y_cm),
            ),
        ]

    return walls


def _extract_openings(
    room: dict[str, Any],
    dimensions: RoomDimensionsCm,
) -> tuple[list[DoorOpeningCm], list[WindowOpeningCm]]:
    features = room.get("features") or {}
    doors: list[DoorOpeningCm] = []
    windows: list[WindowOpeningCm] = []

    door = features.get("door")
    if isinstance(door, dict):
        y_range = door.get("y_range") or [0.0, 0.0]
        y0, y1 = float(y_range[0]), float(y_range[1])
        doors.append(
            DoorOpeningCm(
                opening_id="door_main",
                start_cm=Point2DCm(x_cm=0.0, y_cm=y0),
                end_cm=Point2DCm(x_cm=0.0, y_cm=y1),
                panel_length_cm=float(door.get("panel_length", abs(y1 - y0) or 30.0)),
                opens_towards=door.get("opens_towards"),
            )
        )

    windows_cfg = features.get("windows")
    if isinstance(windows_cfg, dict):
        y_range = windows_cfg.get("range_y") or [0.0, dimensions.depth_y_cm]
        y0, y1 = float(y_range[0]), float(y_range[1])
        z_range = windows_cfg.get("z_range") or [None, None]
        split = windows_cfg.get("split") or {}
        windows.append(
            WindowOpeningCm(
                opening_id="window_main",
                start_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=y0),
                end_cm=Point2DCm(x_cm=dimensions.length_x_cm, y_cm=y1),
                z_min_cm=float(z_range[0]) if z_range[0] is not None else None,
                z_max_cm=float(z_range[1]) if z_range[1] is not None else None,
                panel_count=int(split.get("panels", 1)),
                frame_cm=float(split.get("frame_cm", 0.0)),
            )
        )

    return (doors, windows)


def _extract_furniture(payload: dict[str, Any]) -> list[FurniturePlacementCm]:
    furniture_items = payload.get("furniture") or []
    placements: list[FurniturePlacementCm] = []

    for raw in furniture_items:
        dims = raw.get("dims") or {}
        pos = raw.get("pos") or {}
        placement = FurniturePlacementCm(
            placement_id=str(raw.get("id", raw.get("name", "item"))),
            name=str(raw.get("name", raw.get("id", "Item"))),
            kind=str(raw.get("kind", "generic")),
            position_cm=Point2DCm(
                x_cm=float(pos.get("x", 0.0)),
                y_cm=float(pos.get("y", 0.0)),
            ),
            size_cm={
                "x_cm": float(dims.get("x", 1.0)),
                "y_cm": float(dims.get("y", 1.0)),
                "z_cm": float(dims.get("z", 1.0)),
            },
            z_cm=float(pos.get("z", 0.0)),
            color=raw.get("color"),
            wall_mounted=bool(raw.get("wall_mounted", False)),
            notes=raw.get("notes"),
        )
        placements.append(placement)

    return placements


def _extract_fixtures(payload: dict[str, Any]) -> list[SceneFixture]:
    fixtures_payload = payload.get("fixtures") or []
    fixtures: list[SceneFixture] = []

    for raw in fixtures_payload:
        kind = str(raw.get("kind", "light"))
        common = {
            "fixture_id": str(raw.get("id", "fixture")),
            "x_cm": float(raw.get("x", 0.0)),
            "y_cm": float(raw.get("y", 0.0)),
            "z_cm": float(raw.get("z", 0.0)),
            "label": raw.get("label"),
        }
        if kind == "socket":
            fixtures.append(SocketFixture(**common))
        else:
            fixtures.append(LightFixture(**common))

    return fixtures
