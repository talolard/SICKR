"""Step functions and parsing helpers for the floor-plan intake subagent."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDecision,
    FloorPlanIntakeInput,
    FloorPlanIntakeOutcome,
    FloorPlanIntakeState,
    IntakeStepContext,
    RoomType,
)
from ikea_agent.tools.floorplanner.models import (
    ArchitectureScene,
    BaselineFloorPlanScene,
    Point2DCm,
    RoomDimensionsCm,
    WallSegmentCm,
)

_MEASUREMENT_PATTERN = re.compile(
    r"(\d{2,4})(?:\s*cm)?\s*(?:x|by)\s*(\d{2,4})(?:\s*cm)?",
    re.IGNORECASE,
)
_HEIGHT_PATTERN = re.compile(
    r"(?:height|high|ceiling)\s*(?:is\s*)?(\d{2,4})(?:\s*cm)?",
    re.IGNORECASE,
)
_MIN_ORIENTATION_TOKENS = 2

_LIVING_ROOM_TOKENS: tuple[str, ...] = ("living room", "libing room", "lounge", "sitting room")
_KITCHEN_EXPLICIT_TOKENS: tuple[str, ...] = (
    "this is a kitchen",
    "it's a kitchen",
    "its a kitchen",
    "my kitchen",
    "in the kitchen",
    "kitchen remodel",
    "kitchen layout",
)


class RouteSignal(BaseModel):
    """Routing signal emitted by the first intake step."""

    kind: Literal[
        "unsupported_image",
        "complete",
        "ask_dimensions",
        "ask_orientation",
        "ask_constraints",
        "render",
    ]
    assistant_message: str | None = None


async def route_turn(
    ctx: IntakeStepContext[FloorPlanIntakeInput],
) -> RouteSignal:
    """Evaluate one user turn and emit a routing signal for downstream branches."""

    _ingest_payload_heuristic(ctx.state, ctx.inputs)
    kind = _resolve_route_kind(
        state=ctx.state,
        payload=ctx.inputs,
        max_question_rounds=ctx.deps.max_question_rounds,
    )
    if kind == "unsupported_image":
        return RouteSignal(kind=kind)

    decision = await ctx.deps.intake_decider(state=ctx.state, payload=ctx.inputs)
    _apply_decision_updates(ctx.state, decision)
    return RouteSignal(kind=decision.next_action, assistant_message=decision.assistant_message)


def _resolve_route_kind(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
    max_question_rounds: int,
) -> Literal[
    "unsupported_image",
    "complete",
    "ask_dimensions",
    "ask_orientation",
    "ask_constraints",
    "render",
]:
    if payload.images and not payload.allow_continue_without_measurements:
        kind = "unsupported_image"
    elif _is_finish_signal(payload.user_message):
        kind = "complete"
    elif state.last_render is not None and _wants_render_now(payload.user_message):
        kind = "render"
    elif state.length_cm is None or state.depth_cm is None:
        kind = "ask_dimensions"
    elif not state.orientation_context_collected:
        kind = _route_without_orientation(
            state=state,
            payload=payload,
            max_question_rounds=max_question_rounds,
        )
    elif _should_render_now(
        state=state,
        payload=payload,
        max_question_rounds=max_question_rounds,
    ):
        kind = "render"
    else:
        state.question_rounds += 1
        kind = "ask_constraints"

    return kind


def _route_without_orientation(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
    max_question_rounds: int,
) -> Literal["ask_orientation", "ask_constraints", "render"]:
    if not _has_orientation_details(payload.user_message):
        return "ask_orientation"

    state.orientation_context_collected = True
    if _should_render_now(
        state=state,
        payload=payload,
        max_question_rounds=max_question_rounds,
    ):
        return "render"

    state.question_rounds += 1
    return "ask_constraints"


def _should_render_now(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
    max_question_rounds: int,
) -> bool:
    return _wants_render_now(payload.user_message) or state.question_rounds >= max_question_rounds


async def unsupported_image_outcome(
    ctx: IntakeStepContext[RouteSignal],
) -> FloorPlanIntakeOutcome:
    """Return explicit image unsupported outcome and ask whether to continue."""

    _ = ctx.inputs
    return FloorPlanIntakeOutcome(
        status="unsupported_image",
        should_exit=True,
        assistant_message=(
            "I can see you shared pictures. I do not support picture parsing yet. "
            "Should we continue now without exact image-derived measurements, "
            "or pause and wait for image support?"
        ),
        scene_revision=ctx.state.scene_revision,
        collected_summary=_state_summary(ctx.state),
    )


async def complete_outcome(ctx: IntakeStepContext[RouteSignal]) -> FloorPlanIntakeOutcome:
    """Return completion outcome to exit back to parent flow."""

    _ = ctx.inputs
    return FloorPlanIntakeOutcome(
        status="complete",
        should_exit=True,
        assistant_message=ctx.inputs.assistant_message or _default_complete_message(),
        scene_revision=ctx.state.scene_revision,
        render_output=ctx.state.last_render,
        collected_summary=_state_summary(ctx.state),
    )


async def ask_dimensions_outcome(ctx: IntakeStepContext[RouteSignal]) -> FloorPlanIntakeOutcome:
    """Ask the user for approximate room dimensions."""

    _ = ctx.inputs
    return FloorPlanIntakeOutcome(
        status="ask_user",
        should_exit=False,
        assistant_message=ctx.inputs.assistant_message or _default_dimensions_message(),
        scene_revision=ctx.state.scene_revision,
        collected_summary=_state_summary(ctx.state),
    )


async def ask_orientation_outcome(ctx: IntakeStepContext[RouteSignal]) -> FloorPlanIntakeOutcome:
    """Ask for orientation details and room-specific fixed-element context."""

    _ = ctx.inputs
    return FloorPlanIntakeOutcome(
        status="ask_user",
        should_exit=False,
        assistant_message=ctx.inputs.assistant_message or _orientation_prompt(ctx.state.room_type),
        scene_revision=ctx.state.scene_revision,
        collected_summary=_state_summary(ctx.state),
    )


async def ask_constraints_outcome(ctx: IntakeStepContext[RouteSignal]) -> FloorPlanIntakeOutcome:
    """Ask for architectural constraints before rendering a draft."""

    _ = ctx.inputs
    return FloorPlanIntakeOutcome(
        status="ask_user",
        should_exit=False,
        assistant_message=ctx.inputs.assistant_message or _default_constraints_message(),
        scene_revision=ctx.state.scene_revision,
        collected_summary=_state_summary(ctx.state),
    )


async def render_draft_outcome(ctx: IntakeStepContext[RouteSignal]) -> FloorPlanIntakeOutcome:
    """Render a draft floor-plan revision from collected constraints."""

    _ = ctx.inputs
    scene = _build_scene(ctx.state)
    next_revision = ctx.state.scene_revision + 1
    render_output = ctx.deps.floor_plan_renderer(
        scene=scene,
        scene_revision=next_revision,
        current_scene=ctx.state.current_scene,
        output_dir=ctx.deps.output_dir,
        include_image_bytes=False,
    )
    ctx.state.current_scene = scene
    ctx.state.scene_revision = next_revision
    ctx.state.last_render = render_output

    return FloorPlanIntakeOutcome(
        status="rendered_draft",
        should_exit=False,
        assistant_message=ctx.inputs.assistant_message or _default_render_message(),
        scene_revision=ctx.state.scene_revision,
        render_output=render_output,
        collected_summary=_state_summary(ctx.state),
    )


def _ingest_payload_heuristic(
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
) -> None:
    state.latest_input = payload
    user_text = payload.user_message.strip()
    state.room_type = _infer_room_type(user_text, state.room_type)

    dims = _parse_dimensions_cm(user_text)
    if dims is not None:
        state.length_cm, state.depth_cm = dims

    height = _parse_height_cm(user_text)
    if height is not None:
        state.wall_height_cm = height

    new_constraints = _extract_fixed_constraints(user_text)
    for constraint in new_constraints:
        if constraint not in state.fixed_constraints:
            state.fixed_constraints.append(constraint)


def _apply_decision_updates(
    state: FloorPlanIntakeState,
    decision: FloorPlanIntakeDecision,
) -> None:
    if decision.room_type is not None:
        state.room_type = decision.room_type
    if decision.length_cm is not None:
        state.length_cm = decision.length_cm
    if decision.depth_cm is not None:
        state.depth_cm = decision.depth_cm
    if decision.wall_height_cm is not None:
        state.wall_height_cm = decision.wall_height_cm
    if decision.orientation_context_collected is not None:
        state.orientation_context_collected = decision.orientation_context_collected
    for constraint in decision.fixed_constraints:
        normalized = constraint.strip().lower()
        if normalized and normalized not in state.fixed_constraints:
            state.fixed_constraints.append(normalized)


def _default_complete_message() -> str:
    return (
        "Understood. We can stop here and return to the parent flow. "
        "You can always come back for another refinement pass later."
    )


def _default_dimensions_message() -> str:
    return (
        "Give me a rough room size first (for example, 300 by 400 cm). "
        "Approximate values are fine and we will iterate together. "
        "At any point, you can say 'let's move on'."
    )


def _default_constraints_message() -> str:
    return (
        "Before we draft, tell me fixed architectural constraints: wall height, "
        "unusual corners/curves/poles, plus any hard-mounted objects. "
        "If movable furniture appears, we'll place it later unless it is fixed "
        "to the wall. Optionally share outlets, radiators/heating, and lights. "
        "You can also say 'let's move on' now."
    )


def _default_render_message() -> str:
    return (
        "I generated an initial floor-plan draft from your input. "
        "Does this look right, or do you want corrections? "
        "You can reply with corrections, 'that's close enough', or 'let's give up'."
    )


def _parse_dimensions_cm(text: str) -> tuple[float, float] | None:
    match = _MEASUREMENT_PATTERN.search(text)
    if match is None:
        return None
    a = float(match.group(1))
    b = float(match.group(2))
    return (a, b)


def _parse_height_cm(text: str) -> float | None:
    match = _HEIGHT_PATTERN.search(text)
    if match is None:
        return None
    return float(match.group(1))


def _infer_room_type(text: str, current: RoomType) -> RoomType:
    lowered = text.lower()
    if any(token in lowered for token in _LIVING_ROOM_TOKENS):
        return "living_room"
    if any(token in lowered for token in _KITCHEN_EXPLICIT_TOKENS):
        return "kitchen"
    if "bathroom" in lowered:
        return "bathroom"
    if "bedroom" in lowered:
        return "bedroom"
    if "hallway" in lowered or "corridor" in lowered:
        return "hallway"
    return current


def _extract_fixed_constraints(text: str) -> list[str]:
    lowered = text.lower()
    candidates = [
        "radiator",
        "outlet",
        "socket",
        "lighting fixture",
        "mounted bed",
        "counter",
        "island",
        "sink",
        "toilet",
        "shower",
        "refrigerator",
        "smoke vent",
        "pole",
        "curve",
    ]
    return [item for item in candidates if item in lowered]


def _has_orientation_details(text: str) -> bool:
    lowered = text.lower()
    checks = ["door", "window", "left", "right", "back to", "facing", "entrance"]
    return sum(1 for token in checks if token in lowered) >= _MIN_ORIENTATION_TOKENS


def _wants_render_now(text: str) -> bool:
    lowered = text.lower()
    signals = [
        "let's move on",
        "lets move on",
        "move on",
        "draft",
        "draw",
        "render",
        "try again",
        "another draft",
        "update it",
        "correction",
        "correct this",
    ]
    return any(signal in lowered for signal in signals)


def _is_finish_signal(text: str) -> bool:
    lowered = text.lower()
    signals = ["that's perfect", "thats perfect", "close enough", "let's give up", "lets give up"]
    return any(signal in lowered for signal in signals)


def _orientation_prompt(room_type: RoomType) -> str:
    base = (
        "Great. I bet there is at least one door. Stand with your back to the entrance door and "
        "tell me what you see: where is each window, what is on your left, "
        "and what is on your right. If you mention movable furniture, "
        "we'll place it later unless it is wall-mounted/hard to move. "
        "You can always say 'let's move on'."
    )
    if room_type == "bathroom":
        return (
            f"{base} For bathrooms, add shower, sink, toilet locations "
            "and whether their sizes are standard or custom. "
            "Mention any other major fixed elements."
        )
    if room_type == "kitchen":
        return (
            f"{base} For kitchens, add counter run, island, refrigerator, and smoke vent locations."
        )
    if room_type == "hallway":
        return (
            f"{base} For hallways, tell me how many doors are on left and right "
            "and the distance between them."
        )
    if room_type == "bedroom":
        return (
            f"{base} For bedrooms, only call out bed details now "
            "if the bed is fixed/mounted and hard to move."
        )
    if room_type == "living_room":
        return (
            f"{base} For living rooms, focus on fixed architecture and openings first; "
            "movable items like tables/couches should not change room type."
        )
    return base


def _build_scene(state: FloorPlanIntakeState) -> BaselineFloorPlanScene:
    length_cm = state.length_cm or 400.0
    depth_cm = state.depth_cm or 300.0
    wall_height_cm = state.wall_height_cm or 260.0
    walls = [
        WallSegmentCm(
            wall_id="bottom",
            start_cm=Point2DCm(x_cm=0.0, y_cm=0.0),
            end_cm=Point2DCm(x_cm=length_cm, y_cm=0.0),
        ),
        WallSegmentCm(
            wall_id="right",
            start_cm=Point2DCm(x_cm=length_cm, y_cm=0.0),
            end_cm=Point2DCm(x_cm=length_cm, y_cm=depth_cm),
        ),
        WallSegmentCm(
            wall_id="top",
            start_cm=Point2DCm(x_cm=length_cm, y_cm=depth_cm),
            end_cm=Point2DCm(x_cm=0.0, y_cm=depth_cm),
        ),
        WallSegmentCm(
            wall_id="left",
            start_cm=Point2DCm(x_cm=0.0, y_cm=depth_cm),
            end_cm=Point2DCm(x_cm=0.0, y_cm=0.0),
        ),
    ]
    return BaselineFloorPlanScene(
        architecture=ArchitectureScene(
            dimensions_cm=RoomDimensionsCm(
                length_x_cm=length_cm,
                depth_y_cm=depth_cm,
                height_z_cm=wall_height_cm,
            ),
            walls=walls,
            doors=[],
            windows=[],
        ),
        placements=[],
    )


def _state_summary(state: FloorPlanIntakeState) -> dict[str, object]:
    return {
        "room_type": state.room_type,
        "length_cm": state.length_cm,
        "depth_cm": state.depth_cm,
        "wall_height_cm": state.wall_height_cm,
        "orientation_context_collected": state.orientation_context_collected,
        "fixed_constraints": list(state.fixed_constraints),
        "scene_revision": state.scene_revision,
    }
