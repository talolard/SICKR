"""Local toolset for floor-plan intake agent."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Literal

from pydantic_ai import BinaryContent, ModelRetry, RunContext, ToolReturn
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.floor_plan_intake.deps import FloorPlanIntakeDeps
from ikea_agent.chat.agents.shared import (
    SHARED_CONTEXT_TOOL_NAMES,
    build_first_class_agent_toolset,
    floor_plan_repository,
    require_room_id,
    require_thread_id,
    telemetry_context,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.tools.floorplanner.models import (
    FloorPlannerValidationError,
    FloorPlanRenderOutput,
    FloorPlanRenderRequest,
    FloorPlanScene,
    scene_to_summary,
)
from ikea_agent.tools.floorplanner.tool import render_floor_plan as run_floor_planner
from ikea_agent.tools.floorplanner.yaml_codec import dump_scene_yaml, parse_scene_yaml

logger = getLogger(__name__)

TOOL_NAMES: tuple[str, ...] = (
    *SHARED_CONTEXT_TOOL_NAMES,
    "render_floor_plan",
    "load_floor_plan_scene_yaml",
    "export_floor_plan_scene_yaml",
    "confirm_floor_plan_revision",
)

FloorPlanRenderer = Callable[..., tuple[FloorPlanScene, FloorPlanRenderOutput, ToolReturn | None]]
FloorPlanRepositoryFactory = Callable[[ChatRuntime], FloorPlanRepository | None]


@dataclass(frozen=True, slots=True)
class FloorPlanIntakeToolsetServices:
    """Service seams for floor-plan tools."""

    render_floor_plan: FloorPlanRenderer
    get_floor_plan_repository: FloorPlanRepositoryFactory


def default_floor_plan_intake_toolset_services() -> FloorPlanIntakeToolsetServices:
    """Return the current default service bindings for floor-plan tools."""

    return FloorPlanIntakeToolsetServices(
        render_floor_plan=run_floor_planner,
        get_floor_plan_repository=floor_plan_repository,
    )


def _render_floor_plan_with_services(
    ctx: RunContext[FloorPlanIntakeDeps],
    request: FloorPlanRenderRequest,
    *,
    services: FloorPlanIntakeToolsetServices,
) -> dict[str, object] | ToolReturn:
    repository = services.get_floor_plan_repository(ctx.deps.runtime)
    snapshot = ctx.deps.floor_plan_scene_store.get(ctx.deps.state.session_id)
    room_id = require_room_id(ctx.deps.state)
    thread_id = require_thread_id(ctx.deps.state)
    if snapshot is None and repository is not None:
        persisted_snapshot = repository.get_latest_revision(room_id=room_id)
        if persisted_snapshot is not None:
            snapshot = ctx.deps.floor_plan_scene_store.set_with_revision(
                ctx.deps.state.session_id,
                persisted_snapshot.scene,
                revision=persisted_snapshot.revision,
            )
    current_scene = snapshot.scene if snapshot is not None else None
    next_revision = 1 if snapshot is None else snapshot.revision + 1

    try:
        scene, output, _tool_return = services.render_floor_plan(
            request,
            scene_revision=next_revision,
            current_scene=current_scene,
        )
    except (FloorPlannerValidationError, ValueError) as exc:
        logger.exception(
            "render_floor_plan_failed",
            extra=telemetry_context(ctx.deps.state),
        )
        raise ModelRetry(
            "render_floor_plan failed. Correct the `scene`/`changes` payload "
            "(architecture/openings/placement ids/coordinates) and retry. "
            f"Error: {exc}"
        ) from exc

    output_png_path = Path(output.output_png_path)
    output_svg_path = Path(output.output_svg_path)
    if not output_png_path.exists() or not output_svg_path.exists():
        raise ModelRetry("render_floor_plan produced missing output artifacts.")

    stored_png = ctx.deps.attachment_store.save_image_bytes(
        content=output_png_path.read_bytes(),
        mime_type="image/png",
        filename="floor-plan.png",
        room_id=room_id,
        thread_id=thread_id,
        run_id=ctx.deps.state.run_id,
        created_by_tool="render_floor_plan",
        kind="floor_plan_png",
    )
    stored_svg = ctx.deps.attachment_store.save_image_bytes(
        content=output_svg_path.read_bytes(),
        mime_type="image/svg+xml",
        filename="floor-plan.svg",
        room_id=room_id,
        thread_id=thread_id,
        run_id=ctx.deps.state.run_id,
        created_by_tool="render_floor_plan",
        kind="floor_plan_svg",
    )
    summary = scene_to_summary(scene)
    in_memory_snapshot = ctx.deps.floor_plan_scene_store.set(ctx.deps.state.session_id, scene)
    scene_revision = in_memory_snapshot.revision
    if repository is not None:
        persisted_snapshot = repository.save_revision(
            room_id=room_id,
            thread_id=thread_id,
            scene=scene,
            summary=summary,
            svg_asset_id=stored_svg.ref.attachment_id,
            png_asset_id=stored_png.ref.attachment_id,
        )
        ctx.deps.floor_plan_scene_store.set_with_revision(
            ctx.deps.state.session_id,
            scene,
            revision=persisted_snapshot.revision,
        )
        scene_revision = persisted_snapshot.revision
    payload: dict[str, object] = {
        "caption": output.caption,
        "images": [stored_svg.ref, stored_png.ref],
        "scene_revision": scene_revision,
        "scene_level": output.scene_level,
        "warnings": [warning.model_dump(mode="json") for warning in output.warnings],
        "legend_items": output.legend_items,
        "scale_major_step_cm": output.scale_major_step_cm,
        "scene_summary": summary,
        "scene": scene.model_dump(mode="json"),
    }
    logger.info(
        "render_floor_plan_completed",
        extra={
            "output_attachment_id": stored_png.ref.attachment_id,
            "scene_revision": scene_revision,
            "wall_count": summary["wall_count"],
            "door_count": summary["door_count"],
            "window_count": summary["window_count"],
            "placement_count": summary["placement_count"],
            **telemetry_context(ctx.deps.state),
        },
    )
    if request.include_image_bytes:
        return ToolReturn(
            return_value=payload,
            content=[
                BinaryContent(
                    data=output_png_path.read_bytes(),
                    media_type="image/png",
                )
            ],
            metadata={
                "scene_revision": scene_revision,
                "attachment_ids": [
                    stored_svg.ref.attachment_id,
                    stored_png.ref.attachment_id,
                ],
            },
        )
    return payload


def render_floor_plan(
    ctx: RunContext[FloorPlanIntakeDeps],
    request: FloorPlanRenderRequest,
) -> dict[str, object] | ToolReturn:
    """Render and/or update the active floor-plan scene with SVG+PNG outputs."""

    return _render_floor_plan_with_services(
        ctx,
        request,
        services=default_floor_plan_intake_toolset_services(),
    )


def _load_floor_plan_scene_yaml_with_services(
    ctx: RunContext[FloorPlanIntakeDeps],
    yaml_text: str,
    scene_level: Literal["baseline", "detailed"] = "detailed",
    *,
    services: FloorPlanIntakeToolsetServices,
) -> dict[str, object]:
    repository = services.get_floor_plan_repository(ctx.deps.runtime)
    scene = parse_scene_yaml(yaml_text, scene_level=scene_level)
    summary = scene_to_summary(scene)
    snapshot = ctx.deps.floor_plan_scene_store.set(ctx.deps.state.session_id, scene)
    if repository is not None:
        persisted_snapshot = repository.save_revision(
            room_id=require_room_id(ctx.deps.state),
            thread_id=require_thread_id(ctx.deps.state),
            scene=scene,
            summary=summary,
            svg_asset_id=None,
            png_asset_id=None,
        )
        snapshot = ctx.deps.floor_plan_scene_store.set_with_revision(
            ctx.deps.state.session_id,
            scene,
            revision=persisted_snapshot.revision,
        )
    return {
        "message": "Loaded floor-plan scene YAML into session state.",
        "scene_revision": snapshot.revision,
        "scene_level": scene.scene_level,
        "scene_summary": summary,
    }


def load_floor_plan_scene_yaml(
    ctx: RunContext[FloorPlanIntakeDeps],
    yaml_text: str,
    scene_level: Literal["baseline", "detailed"] = "detailed",
) -> dict[str, object]:
    """Load YAML into typed floor-plan scene state for iterative rendering."""

    return _load_floor_plan_scene_yaml_with_services(
        ctx,
        yaml_text,
        scene_level,
        services=default_floor_plan_intake_toolset_services(),
    )


def _export_floor_plan_scene_yaml_with_services(
    ctx: RunContext[FloorPlanIntakeDeps],
    *,
    services: FloorPlanIntakeToolsetServices,
) -> dict[str, object]:
    repository = services.get_floor_plan_repository(ctx.deps.runtime)
    snapshot = ctx.deps.floor_plan_scene_store.get(ctx.deps.state.session_id)
    if snapshot is None and repository is not None:
        persisted_snapshot = repository.get_latest_revision(room_id=require_room_id(ctx.deps.state))
        if persisted_snapshot is not None:
            snapshot = ctx.deps.floor_plan_scene_store.set_with_revision(
                ctx.deps.state.session_id,
                persisted_snapshot.scene,
                revision=persisted_snapshot.revision,
            )
    if snapshot is None:
        raise ValueError("No floor-plan scene is loaded for this session.")
    return {
        "scene_revision": snapshot.revision,
        "yaml": dump_scene_yaml(snapshot.scene),
        "scene_summary": scene_to_summary(snapshot.scene),
    }


def export_floor_plan_scene_yaml(ctx: RunContext[FloorPlanIntakeDeps]) -> dict[str, object]:
    """Export current typed floor-plan scene state to YAML text."""

    return _export_floor_plan_scene_yaml_with_services(
        ctx,
        services=default_floor_plan_intake_toolset_services(),
    )


def _confirm_floor_plan_revision_with_services(
    ctx: RunContext[FloorPlanIntakeDeps],
    revision: int | None = None,
    confirmation_note: str | None = None,
    *,
    services: FloorPlanIntakeToolsetServices,
) -> dict[str, object]:
    repository = services.get_floor_plan_repository(ctx.deps.runtime)
    if repository is None:
        raise ValueError("Floor-plan persistence is unavailable for this runtime.")

    confirmed = repository.confirm_revision(
        room_id=require_room_id(ctx.deps.state),
        revision=revision,
        run_id=ctx.deps.state.run_id,
        confirmation_note=confirmation_note,
    )
    if confirmed is None:
        raise ValueError("No floor-plan revision found to confirm.")

    ctx.deps.floor_plan_scene_store.set_with_revision(
        ctx.deps.state.session_id,
        confirmed.scene,
        revision=confirmed.revision,
    )
    return {
        "message": "Floor-plan revision marked as confirmed.",
        "scene_revision": confirmed.revision,
        "confirmed_at": confirmed.confirmed_at,
        "confirmation_note": confirmed.confirmation_note,
        "scene_summary": confirmed.summary,
        "scene": confirmed.scene.model_dump(mode="json"),
    }


def confirm_floor_plan_revision(
    ctx: RunContext[FloorPlanIntakeDeps],
    revision: int | None = None,
    confirmation_note: str | None = None,
) -> dict[str, object]:
    """Persist explicit user confirmation for a floor-plan revision."""

    return _confirm_floor_plan_revision_with_services(
        ctx,
        revision,
        confirmation_note,
        services=default_floor_plan_intake_toolset_services(),
    )


def build_floor_plan_intake_toolset(
    services: FloorPlanIntakeToolsetServices | None = None,
) -> FunctionToolset[FloorPlanIntakeDeps]:
    """Build toolset for floor-plan intake agent."""

    resolved_services = services or default_floor_plan_intake_toolset_services()

    def render_floor_plan_tool(
        ctx: RunContext[FloorPlanIntakeDeps],
        request: FloorPlanRenderRequest,
    ) -> dict[str, object] | ToolReturn:
        return _render_floor_plan_with_services(ctx, request, services=resolved_services)

    def load_floor_plan_scene_yaml_tool(
        ctx: RunContext[FloorPlanIntakeDeps],
        yaml_text: str,
        scene_level: Literal["baseline", "detailed"] = "detailed",
    ) -> dict[str, object]:
        return _load_floor_plan_scene_yaml_with_services(
            ctx,
            yaml_text,
            scene_level,
            services=resolved_services,
        )

    def export_floor_plan_scene_yaml_tool(
        ctx: RunContext[FloorPlanIntakeDeps],
    ) -> dict[str, object]:
        return _export_floor_plan_scene_yaml_with_services(
            ctx,
            services=resolved_services,
        )

    def confirm_floor_plan_revision_tool(
        ctx: RunContext[FloorPlanIntakeDeps],
        revision: int | None = None,
        confirmation_note: str | None = None,
    ) -> dict[str, object]:
        return _confirm_floor_plan_revision_with_services(
            ctx,
            revision,
            confirmation_note,
            services=resolved_services,
        )

    return build_first_class_agent_toolset(
        local_tools=[
            Tool(render_floor_plan_tool, name="render_floor_plan"),
            Tool(load_floor_plan_scene_yaml_tool, name="load_floor_plan_scene_yaml"),
            Tool(export_floor_plan_scene_yaml_tool, name="export_floor_plan_scene_yaml"),
            Tool(confirm_floor_plan_revision_tool, name="confirm_floor_plan_revision"),
        ]
    )
