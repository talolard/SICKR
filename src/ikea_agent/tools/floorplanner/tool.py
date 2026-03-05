"""Agent-facing floor-plan tool using Renovation-backed rendering."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import BinaryContent, ToolReturn

from ikea_agent.tools.floorplanner.models import FloorPlanRequest
from ikea_agent.tools.floorplanner.renderer import (
    FloorPlannerRenderer,
    FloorPlannerRenderError,
)

DEFAULT_FLOOR_PLANS_DIR = Path("artifacts/floor_plans")


class FloorPlannerToolResult(BaseModel):
    """Typed return payload for successful floor-plan rendering."""

    output_png_path: str
    element_names: list[str]
    wall_count: int
    door_count: int
    window_count: int
    message: str


def render_floor_plan(
    request: FloorPlanRequest,
    output_dir: Path = DEFAULT_FLOOR_PLANS_DIR,
) -> FloorPlannerToolResult | ToolReturn:
    """Render a floor plan and return a typed result or rich `ToolReturn`."""

    renderer = FloorPlannerRenderer()
    try:
        render_result = renderer.render(request, output_dir)
    except FloorPlannerRenderError as exc:
        msg = f"Floor plan rendering failed: {exc}"
        raise ValueError(msg) from exc

    result = FloorPlannerToolResult(
        output_png_path=str(render_result.output_png),
        element_names=[element.name for element in request.elements],
        wall_count=render_result.wall_count,
        door_count=render_result.door_count,
        window_count=render_result.window_count,
        message=(
            "Rendered floor plan. Ask the user to confirm whether shape and openings "
            "match their intent before proceeding."
        ),
    )

    if not request.include_image_bytes:
        return result

    image_bytes = render_result.output_png.read_bytes()
    return ToolReturn(
        return_value=result.model_dump(),
        content=[BinaryContent(data=image_bytes, media_type="image/png")],
        metadata={
            "output_png_path": result.output_png_path,
            "element_names": result.element_names,
            "wall_count": result.wall_count,
            "door_count": result.door_count,
            "window_count": result.window_count,
        },
    )
