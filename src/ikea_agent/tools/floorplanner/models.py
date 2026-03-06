"""Agent-friendly typed floor-plan wrappers around Renovation elements."""

from __future__ import annotations

from math import cos, radians, sin
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CM_PER_METER = 100.0
_MIN_WALL_COUNT = 3


class FloorPlannerValidationError(ValueError):
    """Raised when a floor-plan payload is inconsistent for rendering."""


class PointCm(BaseModel):
    """Cartesian point represented in centimeters."""

    x_cm: float = Field(description="X coordinate in centimeters.")
    y_cm: float = Field(description="Y coordinate in centimeters.")

    def to_meters_tuple(self) -> tuple[float, float]:
        """Convert centimeters to meters for Renovation APIs."""

        return (self.x_cm / _CM_PER_METER, self.y_cm / _CM_PER_METER)


class _BaseElementCm(BaseModel):
    """Common element fields expected from the agent."""

    name: str = Field(
        min_length=1,
        description=(
            "Stable caller-defined identifier for this element. Used for tracking and "
            "debugging tool calls across retries."
        ),
    )
    anchor_point_cm: PointCm = Field(
        description=(
            "Element start point in centimeters for the 2D plan (x/y only). "
            "If your source data is a room object with wall segments, convert each segment "
            "into explicit wall/door/window elements and use the segment start as anchor."
        )
    )
    orientation_angle_deg: float = Field(
        default=0.0,
        description=(
            "Counterclockwise orientation angle in degrees from the X axis. "
            "Use 0 for horizontal-right, 90 for vertical-up, 180 for horizontal-left, "
            "and -90 for vertical-down."
        ),
    )


class WallElementCm(_BaseElementCm):
    """Renovation `wall` element with agent-friendly defaults."""

    type: Literal["wall"] = "wall"
    length_cm: float = Field(
        gt=0.0,
        description="Wall length in centimeters.",
    )
    thickness_cm: float = Field(
        default=10.0,
        gt=0.0,
        description="Wall thickness in centimeters. Defaults to 10 cm.",
    )
    color: str | None = Field(
        default=None,
        description="Optional drawing color (any matplotlib color string).",
    )

    def to_renovation_element(self) -> dict[str, object]:
        """Convert to Renovation kwargs in meters."""

        element: dict[str, object] = {
            "type": self.type,
            "anchor_point": self.anchor_point_cm.to_meters_tuple(),
            "length": self.length_cm / _CM_PER_METER,
            "thickness": self.thickness_cm / _CM_PER_METER,
            "orientation_angle": self.orientation_angle_deg,
        }
        if self.color is not None:
            element["color"] = self.color
        return element

    def extent_points_cm(self) -> tuple[PointCm, PointCm]:
        """Return two points that approximate the wall segment extent."""

        angle_rad = radians(self.orientation_angle_deg)
        end_x = self.anchor_point_cm.x_cm + cos(angle_rad) * self.length_cm
        end_y = self.anchor_point_cm.y_cm + sin(angle_rad) * self.length_cm
        return (self.anchor_point_cm, PointCm(x_cm=end_x, y_cm=end_y))


class DoorElementCm(_BaseElementCm):
    """Renovation `door` element with defaults suitable for quick agent calls."""

    type: Literal["door"] = "door"
    doorway_width_cm: float = Field(
        default=90.0,
        gt=0.0,
        description="Doorway width in centimeters. Defaults to 90 cm.",
    )
    door_width_cm: float = Field(
        default=80.0,
        gt=0.0,
        description="Door leaf width in centimeters. Defaults to 80 cm.",
    )
    thickness_cm: float = Field(
        default=5.0,
        gt=0.0,
        description="Door frame thickness in centimeters. Defaults to 5 cm.",
    )
    to_the_right: bool = Field(
        default=False,
        description="Whether the door opens to the right from the hinge reference.",
    )
    color: str | None = Field(
        default=None,
        description="Optional drawing color (any matplotlib color string).",
    )

    @model_validator(mode="after")
    def validate_widths(self) -> DoorElementCm:
        """Ensure door width is valid, auto-adjusting omitted defaults when needed."""

        fields_set = getattr(self, "__pydantic_fields_set__", set())
        if "door_width_cm" not in fields_set and self.door_width_cm > self.doorway_width_cm:
            # If caller omitted door_width_cm, keep payload ergonomic by matching doorway width.
            self.door_width_cm = self.doorway_width_cm

        if self.door_width_cm > self.doorway_width_cm:
            msg = "door_width_cm must be less than or equal to doorway_width_cm"
            raise FloorPlannerValidationError(msg)
        return self

    def to_renovation_element(self) -> dict[str, object]:
        """Convert to Renovation kwargs in meters."""

        element: dict[str, object] = {
            "type": self.type,
            "anchor_point": self.anchor_point_cm.to_meters_tuple(),
            "doorway_width": self.doorway_width_cm / _CM_PER_METER,
            "door_width": self.door_width_cm / _CM_PER_METER,
            "thickness": self.thickness_cm / _CM_PER_METER,
            "orientation_angle": self.orientation_angle_deg,
            "to_the_right": self.to_the_right,
        }
        if self.color is not None:
            element["color"] = self.color
        return element

    def extent_points_cm(self) -> tuple[PointCm, PointCm]:
        """Return two points that approximate doorway extent for layout bounds."""

        angle_rad = radians(self.orientation_angle_deg)
        end_x = self.anchor_point_cm.x_cm + cos(angle_rad) * self.doorway_width_cm
        end_y = self.anchor_point_cm.y_cm + sin(angle_rad) * self.doorway_width_cm
        return (self.anchor_point_cm, PointCm(x_cm=end_x, y_cm=end_y))


class WindowElementCm(_BaseElementCm):
    """Renovation `window` element with practical defaults."""

    type: Literal["window"] = "window"
    length_cm: float = Field(
        default=120.0,
        gt=0.0,
        description="Window length in centimeters. Defaults to 120 cm.",
    )
    overall_thickness_cm: float = Field(
        default=10.0,
        gt=0.0,
        description="Total window thickness in centimeters. Defaults to 10 cm.",
    )
    single_line_thickness_cm: float = Field(
        default=3.0,
        gt=0.0,
        description="Thickness of each outer line in centimeters. Defaults to 3 cm.",
    )
    color: str | None = Field(
        default=None,
        description="Optional drawing color (any matplotlib color string).",
    )

    @model_validator(mode="after")
    def validate_thicknesses(self) -> WindowElementCm:
        """Ensure a visible interior gap for the window can be drawn."""

        if self.single_line_thickness_cm * 2 >= self.overall_thickness_cm:
            msg = (
                "single_line_thickness_cm must be less than half of overall_thickness_cm "
                "for window rendering"
            )
            raise FloorPlannerValidationError(msg)
        return self

    def to_renovation_element(self) -> dict[str, object]:
        """Convert to Renovation kwargs in meters."""

        element: dict[str, object] = {
            "type": self.type,
            "anchor_point": self.anchor_point_cm.to_meters_tuple(),
            "length": self.length_cm / _CM_PER_METER,
            "overall_thickness": self.overall_thickness_cm / _CM_PER_METER,
            "single_line_thickness": self.single_line_thickness_cm / _CM_PER_METER,
            "orientation_angle": self.orientation_angle_deg,
        }
        if self.color is not None:
            element["color"] = self.color
        return element

    def extent_points_cm(self) -> tuple[PointCm, PointCm]:
        """Return two points that approximate window span for layout bounds."""

        angle_rad = radians(self.orientation_angle_deg)
        end_x = self.anchor_point_cm.x_cm + cos(angle_rad) * self.length_cm
        end_y = self.anchor_point_cm.y_cm + sin(angle_rad) * self.length_cm
        return (self.anchor_point_cm, PointCm(x_cm=end_x, y_cm=end_y))


FloorPlanElementCm = Annotated[
    WallElementCm | DoorElementCm | WindowElementCm,
    Field(discriminator="type"),
]


class FloorPlanRequest(BaseModel):
    """Minimal agent-facing payload for floor-plan rendering."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "elements": [
                        {
                            "type": "wall",
                            "name": "south_wall",
                            "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                            "length_cm": 340.0,
                        },
                        {
                            "type": "door",
                            "name": "entry_door",
                            "anchor_point_cm": {"x_cm": 20.0, "y_cm": 0.0},
                            "orientation_angle_deg": 90.0,
                        },
                        {
                            "type": "wall",
                            "name": "inset_vertical",
                            "anchor_point_cm": {"x_cm": 320.0, "y_cm": 260.0},
                            "length_cm": 70.0,
                            "orientation_angle_deg": -90.0,
                        },
                        {
                            "type": "wall",
                            "name": "inset_horizontal",
                            "anchor_point_cm": {"x_cm": 320.0, "y_cm": 190.0},
                            "length_cm": 20.0,
                            "orientation_angle_deg": 0.0,
                        },
                    ]
                }
            ]
        }
    )

    elements: list[FloorPlanElementCm] = Field(
        min_length=1,
        description=(
            "Flattened 2D floor-plan primitives to render. Provide at least three walls "
            "as explicit wall elements, and model non-rectangular corners as extra wall segments. "
            "This tool does not accept high-level `room/walls/features/furniture` objects "
            "directly; first translate those into `elements`."
        ),
    )
    layout_padding_cm: float = Field(
        default=50.0,
        ge=0.0,
        description=(
            "Padding around inferred element bounds used when auto-generating layout. "
            "Increase when labels or thick walls are clipped. Defaults to 50 cm."
        ),
    )
    include_image_bytes: bool = Field(
        default=False,
        description=(
            "If true, include PNG bytes as binary content in `ToolReturn` so UIs that "
            "support binary tool content can render the image inline."
        ),
    )

    @field_validator("elements")
    @classmethod
    def validate_unique_names(cls, elements: list[FloorPlanElementCm]) -> list[FloorPlanElementCm]:
        """Ensure element names are unique for reliable tool-call traceability."""

        names = [element.name for element in elements]
        if len(names) != len(set(names)):
            msg = "Element names must be unique"
            raise FloorPlannerValidationError(msg)
        return elements

    @model_validator(mode="after")
    def validate_contains_walls(self) -> FloorPlanRequest:
        """Ensure enough walls exist to define a meaningful room context."""

        if self.count_elements("wall") < _MIN_WALL_COUNT:
            msg = "At least three wall elements are required"
            raise FloorPlannerValidationError(msg)
        return self

    def count_elements(self, element_type: str) -> int:
        """Count elements by Renovation type."""

        return sum(1 for element in self.elements if element.type == element_type)

    def _infer_layout_m(self) -> dict[str, float | int | tuple[float, float] | None]:
        """Infer a reasonable Renovation layout from element extents plus padding."""

        points_cm: list[PointCm] = []
        for element in self.elements:
            points_cm.extend(element.extent_points_cm())

        min_x = min(point.x_cm for point in points_cm) - self.layout_padding_cm
        max_x = max(point.x_cm for point in points_cm) + self.layout_padding_cm
        min_y = min(point.y_cm for point in points_cm) - self.layout_padding_cm
        max_y = max(point.y_cm for point in points_cm) + self.layout_padding_cm

        return {
            "bottom_left_corner": (min_x / _CM_PER_METER, min_y / _CM_PER_METER),
            "top_right_corner": (max_x / _CM_PER_METER, max_y / _CM_PER_METER),
            "scale_numerator": 1,
            "scale_denominator": 40,
            "grid_major_step": 0.5,
            "grid_minor_step": 0.1,
        }

    def to_renovation_settings(self, png_dir: str) -> dict[str, object]:
        """Convert request into Renovation settings dictionary."""

        return {
            "project": {
                "dpi": 160,
                "pdf_file": None,
                "png_dir": png_dir,
            },
            "default_layout": self._infer_layout_m(),
            "reusable_elements": {},
            "floor_plans": [
                {
                    "title": {"text": "Floor Plan", "font_size": 16},
                    "elements": [element.to_renovation_element() for element in self.elements],
                }
            ],
        }
