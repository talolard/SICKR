"""Subagent-local wrapper around repository floor-plan rendering tool."""

from __future__ import annotations

from pathlib import Path

from ikea_agent.tools.floorplanner.models import (
    FloorPlanRenderOutput,
    FloorPlanRenderRequest,
    FloorPlanScene,
)
from ikea_agent.tools.floorplanner.tool import render_floor_plan


def render_floor_plan_draft(
    *,
    scene: FloorPlanScene,
    scene_revision: int,
    current_scene: FloorPlanScene | None,
    output_dir: Path,
    include_image_bytes: bool,
) -> FloorPlanRenderOutput:
    """Render one draft floor plan and return typed output."""

    request = FloorPlanRenderRequest(scene=scene, include_image_bytes=include_image_bytes)
    _, output, _ = render_floor_plan(
        request,
        scene_revision=scene_revision,
        current_scene=current_scene,
        output_dir=output_dir,
    )
    return output
