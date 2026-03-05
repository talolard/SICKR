"""Typed domain models for floor-plan requests and renovation conversion."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, isclose

from pydantic import BaseModel, Field, model_validator

_EPSILON = 1e-6


class FloorPlannerValidationError(ValueError):
    """Raised when a floor-plan payload is internally inconsistent."""


class Point2D(BaseModel):
    """Cartesian point in meters used for room geometry."""

    x_m: float
    y_m: float


class WallSegment(BaseModel):
    """Ordered wall segment describing the room perimeter."""

    id: str
    start: Point2D
    end: Point2D
    thickness_m: float = Field(default=0.1, gt=0.0)
    color: str | None = None

    @property
    def length_m(self) -> float:
        """Return Euclidean segment length in meters."""

        dx = self.end.x_m - self.start.x_m
        dy = self.end.y_m - self.start.y_m
        return (dx * dx + dy * dy) ** 0.5

    @property
    def orientation_angle(self) -> float:
        """Return segment orientation angle in degrees for renovation config."""

        dx = self.end.x_m - self.start.x_m
        dy = self.end.y_m - self.start.y_m
        return degrees(atan2(dy, dx))


class DoorOpening(BaseModel):
    """Door opening anchored on a wall by offset from wall start."""

    id: str
    wall_id: str
    offset_from_wall_start_m: float = Field(ge=0.0)
    doorway_width_m: float = Field(gt=0.0)
    door_width_m: float | None = Field(default=None, gt=0.0)
    thickness_m: float = Field(default=0.05, gt=0.0)
    to_the_right: bool = False
    color: str | None = None


class WindowOpening(BaseModel):
    """Window opening anchored on a wall by offset from wall start."""

    id: str
    wall_id: str
    offset_from_wall_start_m: float = Field(ge=0.0)
    length_m: float = Field(gt=0.0)
    overall_thickness_m: float = Field(gt=0.0)
    single_line_thickness_m: float = Field(gt=0.0)


class FurnitureItem(BaseModel):
    """Optional rectangular furniture used for rendering context."""

    id: str
    anchor: Point2D
    width_m: float = Field(gt=0.0)
    depth_m: float = Field(gt=0.0)
    color: str | None = None


class FloorPlanRequest(BaseModel):
    """Top-level payload validated before conversion to renovation config."""

    plan_name: str
    output_filename_stem: str = "floor_plan"
    wall_margin_m: float = Field(default=0.8, ge=0.0)
    walls: list[WallSegment] = Field(min_length=3)
    doors: list[DoorOpening] = Field(default_factory=list)
    windows: list[WindowOpening] = Field(default_factory=list)
    furniture: list[FurnitureItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_geometry(self) -> FloorPlanRequest:
        """Validate perimeter closure, non-crossing walls, and opening placement."""

        _validate_walls(self.walls)

        walls_by_id = {wall.id: wall for wall in self.walls}
        for door in self.doors:
            _validate_opening(
                door.wall_id, door.offset_from_wall_start_m, door.doorway_width_m, walls_by_id
            )

        for window in self.windows:
            _validate_opening(
                window.wall_id, window.offset_from_wall_start_m, window.length_m, walls_by_id
            )

        return self

    def to_renovation_settings(self, png_dir: str) -> dict[str, object]:
        """Convert typed request into the dictionary schema accepted by renovation."""

        walls_by_id = {wall.id: wall for wall in self.walls}
        reusable_elements = [
            *_wall_elements(self.walls),
            *_door_elements(self.doors, walls_by_id),
            *_window_elements(self.windows, walls_by_id),
        ]
        default_layout = _default_layout(self.walls, self.wall_margin_m)

        return {
            "project": {
                "dpi": 160,
                "pdf_file": None,
                "png_dir": png_dir,
            },
            "default_layout": default_layout,
            "reusable_elements": {"room_elements": reusable_elements},
            "floor_plans": [
                {
                    "title": {"text": self.plan_name, "font_size": 16},
                    "inherited_elements": ["room_elements"],
                }
            ],
        }


@dataclass(frozen=True, slots=True)
class OpeningValidationInput:
    """Typed helper for opening checks."""

    wall_id: str
    offset_from_wall_start_m: float
    opening_length_m: float


def _wall_elements(walls: list[WallSegment]) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    for wall in walls:
        wall_element: dict[str, object] = {
            "type": "wall",
            "anchor_point": (wall.start.x_m, wall.start.y_m),
            "length": wall.length_m,
            "thickness": wall.thickness_m,
        }
        if not isclose(wall.orientation_angle, 0.0, abs_tol=_EPSILON):
            wall_element["orientation_angle"] = wall.orientation_angle
        if wall.color is not None:
            wall_element["color"] = wall.color
        elements.append(wall_element)
    return elements


def _door_elements(
    doors: list[DoorOpening],
    walls_by_id: dict[str, WallSegment],
) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    for door in doors:
        wall = walls_by_id[door.wall_id]
        anchor = _point_on_wall(wall, door.offset_from_wall_start_m)
        door_element: dict[str, object] = {
            "type": "door",
            "anchor_point": (anchor.x_m, anchor.y_m),
            "doorway_width": door.doorway_width_m,
            "door_width": door.door_width_m or max(door.doorway_width_m - 0.1, 0.1),
            "thickness": door.thickness_m,
        }
        if not isclose(wall.orientation_angle, 0.0, abs_tol=_EPSILON):
            door_element["orientation_angle"] = wall.orientation_angle
        if door.to_the_right:
            door_element["to_the_right"] = True
        if door.color is not None:
            door_element["color"] = door.color
        elements.append(door_element)
    return elements


def _window_elements(
    windows: list[WindowOpening],
    walls_by_id: dict[str, WallSegment],
) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    for window in windows:
        wall = walls_by_id[window.wall_id]
        anchor = _point_on_wall(wall, window.offset_from_wall_start_m)
        window_element: dict[str, object] = {
            "type": "window",
            "anchor_point": (anchor.x_m, anchor.y_m),
            "length": window.length_m,
            "overall_thickness": window.overall_thickness_m,
            "single_line_thickness": window.single_line_thickness_m,
        }
        if not isclose(wall.orientation_angle, 0.0, abs_tol=_EPSILON):
            window_element["orientation_angle"] = wall.orientation_angle
        elements.append(window_element)
    return elements


def _default_layout(walls: list[WallSegment], wall_margin_m: float) -> dict[str, object]:
    min_x, max_x, min_y, max_y = _compute_bounds(walls, wall_margin_m)
    return {
        "bottom_left_corner": (min_x, min_y),
        "top_right_corner": (max_x, max_y),
        "scale_numerator": 1,
        "scale_denominator": 40,
        "grid_major_step": 0.5,
        "grid_minor_step": 0.1,
    }


def _validate_walls(walls: list[WallSegment]) -> None:
    for index, wall in enumerate(walls):
        if wall.length_m <= _EPSILON:
            msg = f"Wall '{wall.id}' has zero or negative length"
            raise FloorPlannerValidationError(msg)

        next_wall = walls[(index + 1) % len(walls)]
        if not _points_close(wall.end, next_wall.start):
            msg = (
                "Walls must form a closed ordered perimeter; "
                f"'{wall.id}'.end does not match '{next_wall.id}'.start"
            )
            raise FloorPlannerValidationError(msg)

    segments = [(wall.start, wall.end, wall.id) for wall in walls]
    for i, first in enumerate(segments):
        for j in range(i + 1, len(segments)):
            if j in {i - 1, i + 1} or (i == 0 and j == len(segments) - 1):
                continue
            second = segments[j]
            if _segments_intersect(first[0], first[1], second[0], second[1]):
                msg = f"Walls '{first[2]}' and '{second[2]}' intersect"
                raise FloorPlannerValidationError(msg)


def _validate_opening(
    wall_id: str,
    offset_from_wall_start_m: float,
    opening_length_m: float,
    walls_by_id: dict[str, WallSegment],
) -> None:
    wall = walls_by_id.get(wall_id)
    if wall is None:
        msg = f"Unknown wall reference '{wall_id}'"
        raise FloorPlannerValidationError(msg)

    if offset_from_wall_start_m < 0:
        msg = f"Opening on wall '{wall_id}' has negative offset"
        raise FloorPlannerValidationError(msg)

    if opening_length_m <= 0:
        msg = f"Opening on wall '{wall_id}' must have positive length"
        raise FloorPlannerValidationError(msg)

    if offset_from_wall_start_m + opening_length_m > wall.length_m + _EPSILON:
        msg = f"Opening on wall '{wall_id}' exceeds wall length"
        raise FloorPlannerValidationError(msg)


def _compute_bounds(
    walls: list[WallSegment],
    margin_m: float,
) -> tuple[float, float, float, float]:
    x_values = [point.x_m for wall in walls for point in (wall.start, wall.end)]
    y_values = [point.y_m for wall in walls for point in (wall.start, wall.end)]
    return (
        min(x_values) - margin_m,
        max(x_values) + margin_m,
        min(y_values) - margin_m,
        max(y_values) + margin_m,
    )


def _point_on_wall(wall: WallSegment, offset_m: float) -> Point2D:
    ratio = offset_m / wall.length_m
    return Point2D(
        x_m=wall.start.x_m + ratio * (wall.end.x_m - wall.start.x_m),
        y_m=wall.start.y_m + ratio * (wall.end.y_m - wall.start.y_m),
    )


def _points_close(first: Point2D, second: Point2D) -> bool:
    return isclose(first.x_m, second.x_m, abs_tol=_EPSILON) and isclose(
        first.y_m, second.y_m, abs_tol=_EPSILON
    )


def _segments_intersect(a1: Point2D, a2: Point2D, b1: Point2D, b2: Point2D) -> bool:
    def orientation(p: Point2D, q: Point2D, r: Point2D) -> float:
        return (q.y_m - p.y_m) * (r.x_m - q.x_m) - (q.x_m - p.x_m) * (r.y_m - q.y_m)

    def on_segment(p: Point2D, q: Point2D, r: Point2D) -> bool:
        return (
            min(p.x_m, r.x_m) - _EPSILON <= q.x_m <= max(p.x_m, r.x_m) + _EPSILON
            and min(p.y_m, r.y_m) - _EPSILON <= q.y_m <= max(p.y_m, r.y_m) + _EPSILON
        )

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True

    if isclose(o1, 0.0, abs_tol=_EPSILON) and on_segment(a1, b1, a2):
        return True
    if isclose(o2, 0.0, abs_tol=_EPSILON) and on_segment(a1, b2, a2):
        return True
    if isclose(o3, 0.0, abs_tol=_EPSILON) and on_segment(b1, a1, b2):
        return True
    return isclose(o4, 0.0, abs_tol=_EPSILON) and on_segment(b1, a2, b2)
