"""Tools package exposing typed domain tools and agent bridge helpers."""

from tal_maria_ikea.tools.contracts import ToolExecutionResult, ToolProtocol
from tal_maria_ikea.tools.floor_planner_models import (
    DoorOpening,
    FloorPlannerValidationError,
    FloorPlanRequest,
    FurnitureItem,
    Point2D,
    WallSegment,
    WindowOpening,
)
from tal_maria_ikea.tools.floor_planner_renderer import (
    FloorPlannerRenderer,
    FloorPlannerRenderError,
    FloorPlanRenderResult,
)
from tal_maria_ikea.tools.floor_planner_tool import FloorPlannerTool, register_floor_planner_tool

__all__ = [
    "DoorOpening",
    "FloorPlanRenderResult",
    "FloorPlanRequest",
    "FloorPlannerRenderError",
    "FloorPlannerRenderer",
    "FloorPlannerTool",
    "FloorPlannerValidationError",
    "FurnitureItem",
    "Point2D",
    "ToolExecutionResult",
    "ToolProtocol",
    "WallSegment",
    "WindowOpening",
    "register_floor_planner_tool",
]
