"""Typed scene contracts for the in-repo SVG floor-plan renderer.

These models replace renovation-specific wrappers with a scene-first contract designed
for iterative agent updates. The scene keeps geometric numbers in structured fields,
while rendering output remains an artifact concern.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class FloorPlannerValidationError(ValueError):
    """Raised when a scene payload is structurally inconsistent."""


class Point2DCm(BaseModel):
    """2D Cartesian point in centimeters."""

    x_cm: float
    y_cm: float


class Size3DCm(BaseModel):
    """Axis-aligned size in centimeters."""

    x_cm: float = Field(gt=0.0)
    y_cm: float = Field(gt=0.0)
    z_cm: float = Field(gt=0.0)


class RoomDimensionsCm(BaseModel):
    """Room envelope dimensions in centimeters."""

    length_x_cm: float = Field(gt=0.0)
    depth_y_cm: float = Field(gt=0.0)
    height_z_cm: float = Field(gt=0.0)


class WallSegmentCm(BaseModel):
    """One wall segment in top-down coordinates."""

    wall_id: str = Field(min_length=1)
    start_cm: Point2DCm
    end_cm: Point2DCm
    thickness_cm: float = Field(default=10.0, gt=0.0)
    color: str | None = None
    label: str | None = None


class DoorOpeningCm(BaseModel):
    """Door opening represented as a wall segment and swing metadata."""

    opening_id: str = Field(min_length=1)
    start_cm: Point2DCm
    end_cm: Point2DCm
    z_min_cm: float | None = Field(default=None, ge=0.0)
    z_max_cm: float | None = Field(default=None, ge=0.0)
    opens_towards: str | None = None
    panel_length_cm: float | None = Field(default=None, gt=0.0)
    label: str | None = None

    @model_validator(mode="after")
    def validate_non_zero_span(self) -> DoorOpeningCm:
        """Ensure door geometry is coherent across plan and optional elevation fields."""

        if (
            self.z_min_cm is not None
            and self.z_max_cm is not None
            and self.z_max_cm < self.z_min_cm
        ):
            msg = "z_max_cm must be greater than or equal to z_min_cm"
            raise FloorPlannerValidationError(msg)

        if self.start_cm.x_cm == self.end_cm.x_cm and self.start_cm.y_cm == self.end_cm.y_cm:
            msg = "Door opening segment cannot be zero-length"
            raise FloorPlannerValidationError(msg)
        return self


class WindowOpeningCm(BaseModel):
    """Window opening represented as a wall segment with optional vertical range."""

    opening_id: str = Field(min_length=1)
    start_cm: Point2DCm
    end_cm: Point2DCm
    z_min_cm: float | None = Field(default=None, ge=0.0)
    z_max_cm: float | None = Field(default=None, ge=0.0)
    panel_count: int = Field(default=1, ge=1)
    frame_cm: float = Field(default=0.0, ge=0.0)
    label: str | None = None

    @model_validator(mode="after")
    def validate_vertical_range(self) -> WindowOpeningCm:
        """Keep optional z-range coherent when present."""

        if (
            self.z_min_cm is not None
            and self.z_max_cm is not None
            and self.z_max_cm < self.z_min_cm
        ):
            msg = "z_max_cm must be greater than or equal to z_min_cm"
            raise FloorPlannerValidationError(msg)
        if self.start_cm.x_cm == self.end_cm.x_cm and self.start_cm.y_cm == self.end_cm.y_cm:
            msg = "Window opening segment cannot be zero-length"
            raise FloorPlannerValidationError(msg)
        return self


class ArchitectureScene(BaseModel):
    """Room shell and openings used by all scene levels."""

    dimensions_cm: RoomDimensionsCm
    walls: list[WallSegmentCm] = Field(min_length=3)
    doors: list[DoorOpeningCm] = Field(default_factory=list)
    windows: list[WindowOpeningCm] = Field(default_factory=list)
    outline_cm: list[Point2DCm] | None = None

    @field_validator("walls")
    @classmethod
    def unique_wall_ids(cls, walls: list[WallSegmentCm]) -> list[WallSegmentCm]:
        """Ensure wall ids remain stable for downstream references."""

        ids = [wall.wall_id for wall in walls]
        if len(ids) != len(set(ids)):
            msg = "Wall ids must be unique"
            raise FloorPlannerValidationError(msg)
        return walls

    @model_validator(mode="after")
    def validate_openings_on_walls(self) -> ArchitectureScene:
        """Require doors and windows to lie on existing wall segments."""

        for door in self.doors:
            if not any(
                _segment_belongs_to_wall(door.start_cm, door.end_cm, wall) for wall in self.walls
            ):
                msg = f"Door `{door.opening_id}` must lie on a wall segment."
                raise FloorPlannerValidationError(msg)
        for window in self.windows:
            if not any(
                _segment_belongs_to_wall(window.start_cm, window.end_cm, wall)
                for wall in self.walls
            ):
                msg = f"Window `{window.opening_id}` must lie on a wall segment."
                raise FloorPlannerValidationError(msg)
        return self


def _point_on_segment(point: Point2DCm, start: Point2DCm, end: Point2DCm) -> bool:
    """Return true when point lies on finite segment start->end."""

    epsilon = 1e-3
    dx = end.x_cm - start.x_cm
    dy = end.y_cm - start.y_cm
    length_sq = dx * dx + dy * dy
    if length_sq <= epsilon:
        return False

    cross = (point.x_cm - start.x_cm) * dy - (point.y_cm - start.y_cm) * dx
    if abs(cross) > epsilon * (abs(dx) + abs(dy) + 1.0):
        return False

    dot = (point.x_cm - start.x_cm) * dx + (point.y_cm - start.y_cm) * dy
    return -epsilon <= dot <= length_sq + epsilon


def _segment_belongs_to_wall(
    opening_start: Point2DCm,
    opening_end: Point2DCm,
    wall: WallSegmentCm,
) -> bool:
    """Return true when opening endpoints both lie on the same wall segment."""

    return _point_on_segment(opening_start, wall.start_cm, wall.end_cm) and _point_on_segment(
        opening_end, wall.start_cm, wall.end_cm
    )


class FurniturePlacementCm(BaseModel):
    """Generic top-down placement with optional vertical semantics."""

    placement_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: str = Field(default="generic")
    position_cm: Point2DCm
    size_cm: Size3DCm
    z_cm: float = Field(default=0.0, ge=0.0)
    color: str | None = None
    wall_mounted: bool = False
    stacked_on_placement_id: str | None = None
    label: str | None = None
    notes: str | None = None


class ElectricalSocketCm(BaseModel):
    """Socket marker in 2D with optional mounting height."""

    fixture_id: str = Field(min_length=1)
    x_cm: float
    y_cm: float
    z_cm: float = Field(default=0.0, ge=0.0)
    label: str | None = None


class LightFixtureCm(BaseModel):
    """Light marker in 2D with optional mounting height."""

    fixture_id: str = Field(min_length=1)
    x_cm: float
    y_cm: float
    z_cm: float = Field(default=0.0, ge=0.0)
    label: str | None = None


ElectricalFixtureCm = Annotated[
    ElectricalSocketCm | LightFixtureCm, Field(discriminator="fixture_kind")
]


class SocketFixture(ElectricalSocketCm):
    """Discriminated socket fixture."""

    fixture_kind: Literal["socket"] = "socket"


class LightFixture(LightFixtureCm):
    """Discriminated light fixture."""

    fixture_kind: Literal["light"] = "light"


SceneFixture = Annotated[SocketFixture | LightFixture, Field(discriminator="fixture_kind")]


class BaselineFloorPlanScene(BaseModel):
    """Baseline scene for initial user confirmation before fine detail placement."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
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
                                "wall_id": "bottom",
                                "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                                "end_cm": {"x_cm": 340.0, "y_cm": 0.0},
                            },
                            {
                                "wall_id": "right",
                                "start_cm": {"x_cm": 340.0, "y_cm": 0.0},
                                "end_cm": {"x_cm": 340.0, "y_cm": 190.0},
                            },
                            {
                                "wall_id": "left",
                                "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                                "end_cm": {"x_cm": 0.0, "y_cm": 260.0},
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
            ]
        }
    )

    scene_level: Literal["baseline"] = "baseline"
    architecture: ArchitectureScene
    placements: list[FurniturePlacementCm] = Field(default_factory=list)

    @field_validator("placements")
    @classmethod
    def unique_placement_ids(
        cls, placements: list[FurniturePlacementCm]
    ) -> list[FurniturePlacementCm]:
        """Keep placement ids unique so change-sets remain deterministic."""

        ids = [placement.placement_id for placement in placements]
        if len(ids) != len(set(ids)):
            msg = "Placement ids must be unique"
            raise FloorPlannerValidationError(msg)
        return placements


class DetailedFloorPlanScene(BaseModel):
    """Detailed scene extends baseline with fixtures and optional tagged extras."""

    scene_level: Literal["detailed"] = "detailed"
    architecture: ArchitectureScene
    placements: list[FurniturePlacementCm] = Field(default_factory=list)
    fixtures: list[SceneFixture] = Field(default_factory=list)
    tagged_items: list[FurniturePlacementCm] = Field(default_factory=list)

    @field_validator("placements")
    @classmethod
    def unique_placement_ids(
        cls, placements: list[FurniturePlacementCm]
    ) -> list[FurniturePlacementCm]:
        """Keep placement ids unique so change-sets remain deterministic."""

        ids = [placement.placement_id for placement in placements]
        if len(ids) != len(set(ids)):
            msg = "Placement ids must be unique"
            raise FloorPlannerValidationError(msg)
        return placements


FloorPlanScene = Annotated[
    BaselineFloorPlanScene | DetailedFloorPlanScene,
    Field(discriminator="scene_level"),
]


class SceneChangeSet(BaseModel):
    """Incremental mutations that can be applied on top of current scene state."""

    replace_scene: FloorPlanScene | None = None
    upsert_placements: list[FurniturePlacementCm] = Field(default_factory=list)
    remove_placement_ids: list[str] = Field(default_factory=list)
    upsert_fixtures: list[SceneFixture] = Field(default_factory=list)
    remove_fixture_ids: list[str] = Field(default_factory=list)


class FloorPlanRenderRequest(BaseModel):
    """Render request that supports either full scene replacement or incremental updates."""

    scene: FloorPlanScene | None = Field(
        default=None,
        description=(
            "Full scene payload. Provide this for initial rendering or a complete replacement."
        ),
    )
    changes: SceneChangeSet | None = Field(
        default=None,
        description=(
            "Incremental scene mutations. Use this for add/update/remove placement workflows."
        ),
    )
    render_preset: Literal["confirm", "detailed"] = "confirm"
    include_image_bytes: bool = Field(
        default=True,
        description=(
            "If true, include PNG bytes in ToolReturn binary content for model-side vision use."
        ),
    )

    @model_validator(mode="after")
    def validate_payload_shape(self) -> FloorPlanRenderRequest:
        """Require scene or changes so calls cannot be empty."""

        if self.scene is None and self.changes is None:
            msg = "At least one of `scene` or `changes` must be provided"
            raise FloorPlannerValidationError(msg)
        return self


class RenderWarning(BaseModel):
    """Structured render warning with machine-friendly severity."""

    severity: Literal["info", "warn", "error"]
    code: str
    message: str
    entity_id: str | None = None


class FloorPlanRenderOutput(BaseModel):
    """Typed result returned by the scene renderer tool."""

    caption: str
    scene_revision: int
    scene_level: Literal["baseline", "detailed"]
    output_svg_path: str
    output_png_path: str
    warnings: list[RenderWarning]
    legend_items: list[str]
    scale_major_step_cm: int
    scene: FloorPlanScene


def infer_outline_from_dimensions(dimensions: RoomDimensionsCm) -> list[Point2DCm]:
    """Return a rectangle outline from room dimensions when no explicit outline exists."""

    return [
        Point2DCm(x_cm=0.0, y_cm=0.0),
        Point2DCm(x_cm=dimensions.length_x_cm, y_cm=0.0),
        Point2DCm(x_cm=dimensions.length_x_cm, y_cm=dimensions.depth_y_cm),
        Point2DCm(x_cm=0.0, y_cm=dimensions.depth_y_cm),
    ]


def clone_scene(scene: FloorPlanScene) -> FloorPlanScene:
    """Create an immutable-style deep copy of a scene object."""

    scene_adapter = TypeAdapter(FloorPlanScene)
    return scene_adapter.validate_python(scene.model_dump(mode="python"))


def apply_changes(scene: FloorPlanScene, changes: SceneChangeSet) -> FloorPlanScene:
    """Apply a change-set and return a new scene instance without mutating inputs."""

    if changes.replace_scene is not None:
        working: FloorPlanScene = clone_scene(changes.replace_scene)
    else:
        working = clone_scene(scene)

    placement_map = {item.placement_id: item for item in working.placements}
    for placement_id in changes.remove_placement_ids:
        placement_map.pop(placement_id, None)
    for item in changes.upsert_placements:
        placement_map[item.placement_id] = item
    working.placements = list(placement_map.values())

    if isinstance(working, DetailedFloorPlanScene):
        fixture_map = {fixture.fixture_id: fixture for fixture in working.fixtures}
        for fixture_id in changes.remove_fixture_ids:
            fixture_map.pop(fixture_id, None)
        for fixture in changes.upsert_fixtures:
            fixture_map[fixture.fixture_id] = fixture
        working.fixtures = list(fixture_map.values())

    return working


def scene_to_summary(scene: FloorPlanScene) -> dict[str, Any]:
    """Return a compact summary useful for tool messages and tests."""

    fixture_count = len(scene.fixtures) if isinstance(scene, DetailedFloorPlanScene) else 0
    return {
        "scene_level": scene.scene_level,
        "wall_count": len(scene.architecture.walls),
        "door_count": len(scene.architecture.doors),
        "window_count": len(scene.architecture.windows),
        "placement_count": len(scene.placements),
        "fixture_count": fixture_count,
        "wall_labels": [wall.label or wall.wall_id for wall in scene.architecture.walls],
        "door_labels": [door.label or door.opening_id for door in scene.architecture.doors],
        "window_labels": [
            window.label or window.opening_id for window in scene.architecture.windows
        ],
    }
