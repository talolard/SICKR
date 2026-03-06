"""Agent-facing floor-plan scene tool helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import BinaryContent, ToolReturn

from ikea_agent.tools.floorplanner.models import (
    FloorPlannerValidationError,
    FloorPlanRenderOutput,
    FloorPlanRenderRequest,
    FloorPlanScene,
    apply_changes,
    scene_to_summary,
)
from ikea_agent.tools.floorplanner.renderer import (
    FloorPlannerRenderArtifacts,
    FloorPlannerRenderer,
    FloorPlannerRenderError,
)

DEFAULT_FLOOR_PLANS_DIR = Path("artifacts/floor_plans")


def resolve_scene(
    *,
    current_scene: FloorPlanScene | None,
    request: FloorPlanRenderRequest,
) -> FloorPlanScene:
    """Resolve target scene from current state and request payload."""

    if request.scene is not None:
        resolved = request.scene
    elif current_scene is not None:
        resolved = current_scene
    else:
        msg = "No existing scene found. Provide `scene` in request for initial render."
        raise FloorPlannerValidationError(msg)

    if request.changes is not None:
        resolved = apply_changes(resolved, request.changes)
    return resolved


def build_render_output(
    *,
    scene: FloorPlanScene,
    render_result: FloorPlannerRenderArtifacts,
    scene_revision: int,
) -> FloorPlanRenderOutput:
    """Create typed render output from scene and renderer artifacts."""

    summary = scene_to_summary(scene)
    caption = (
        "Rendered floor plan scene. "
        f"Walls: {summary['wall_count']}, doors: {summary['door_count']}, "
        f"windows: {summary['window_count']}, placements: {summary['placement_count']}."
    )
    return FloorPlanRenderOutput(
        caption=caption,
        scene_revision=scene_revision,
        scene_level=scene.scene_level,
        output_svg_path=str(render_result.output_svg),
        output_png_path=str(render_result.output_png),
        warnings=render_result.warnings,
        legend_items=render_result.legend_items,
        scale_major_step_cm=render_result.scale_major_step_cm,
        scene=scene,
    )


def render_floor_plan(
    request: FloorPlanRenderRequest,
    *,
    scene_revision: int,
    current_scene: FloorPlanScene | None,
    output_dir: Path = DEFAULT_FLOOR_PLANS_DIR,
) -> tuple[FloorPlanScene, FloorPlanRenderOutput, ToolReturn | None]:
    """Render a floor plan scene and optionally include PNG binary content."""

    scene = resolve_scene(current_scene=current_scene, request=request)
    renderer = FloorPlannerRenderer()

    try:
        render_result = renderer.render(scene, output_dir)
    except FloorPlannerRenderError as exc:
        msg = f"Floor plan rendering failed: {exc}"
        raise ValueError(msg) from exc

    output = build_render_output(
        scene=scene,
        render_result=render_result,
        scene_revision=scene_revision,
    )

    tool_return: ToolReturn | None = None
    if request.include_image_bytes:
        png_bytes = render_result.output_png.read_bytes()
        tool_return = ToolReturn(
            return_value=output.model_dump(mode="json"),
            content=[BinaryContent(data=png_bytes, media_type="image/png")],
            metadata={
                "scene_revision": output.scene_revision,
                "scene_level": output.scene_level,
                "output_svg_path": output.output_svg_path,
                "output_png_path": output.output_png_path,
                "warning_count": len(output.warnings),
            },
        )

    return (scene, output, tool_return)
