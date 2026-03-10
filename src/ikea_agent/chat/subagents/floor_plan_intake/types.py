"""Typed contracts for the floor-plan intake subagent graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, Field
from pydantic_graph.beta.step import StepContext

from ikea_agent.tools.floorplanner.models import FloorPlanRenderOutput, FloorPlanScene

RoomType = Literal["bathroom", "kitchen", "bedroom", "living_room", "hallway", "other"]


class FloorPlanIntakeInput(BaseModel):
    """Parent-provided user turn payload for floor-plan intake."""

    user_message: str
    images: list[str] = Field(default_factory=list)
    thread_id: str | None = None
    allow_continue_without_measurements: bool = False


class FloorPlanIntakeOutcome(BaseModel):
    """Subagent output consumed by parent orchestration."""

    status: Literal["ask_user", "rendered_draft", "complete", "unsupported_image"]
    should_exit: bool
    assistant_message: str
    scene_revision: int = 0
    render_output: FloorPlanRenderOutput | None = None
    collected_summary: dict[str, object] = Field(default_factory=dict)


class FloorPlanIntakeDecision(BaseModel):
    """Model-produced intake decision for one user turn."""

    next_action: Literal[
        "complete",
        "ask_dimensions",
        "ask_orientation",
        "ask_constraints",
        "render",
    ]
    assistant_message: str = Field(
        min_length=1,
        description="Response shown to user for the selected action.",
    )
    room_type: RoomType | None = None
    width_cm: float | None = None
    length_cm: float | None = None
    height_cm: float | None = None
    orientation_context_collected: bool | None = None
    fixed_constraints: list[str] = Field(default_factory=list)


class FloorPlanRenderCallable(Protocol):
    """Typed renderer callable used by graph nodes for floor-plan draft generation."""

    def __call__(
        self,
        *,
        scene: FloorPlanScene,
        scene_revision: int,
        current_scene: FloorPlanScene | None,
        output_dir: Path,
        include_image_bytes: bool,
    ) -> FloorPlanRenderOutput:
        """Render one scene revision and return canonical render output."""
        ...


class FloorPlanIntakeDeciderCallable(Protocol):
    """Typed model-backed decider callable for subagent routing."""

    async def __call__(
        self,
        *,
        state: FloorPlanIntakeState,
        payload: FloorPlanIntakeInput,
    ) -> FloorPlanIntakeDecision:
        """Return structured next-step decision and extracted fields."""
        ...


@dataclass(slots=True)
class FloorPlanIntakeState:
    """Mutable graph state for iterative intake and draft-render loop."""

    latest_input: FloorPlanIntakeInput | None = None
    room_type: RoomType = "other"
    width_cm: float | None = None
    length_cm: float | None = None
    height_cm: float | None = None
    height_assumed_default: bool = False
    height_default_notified: bool = False
    orientation_context_collected: bool = False
    fixed_constraints: list[str] = field(default_factory=list)
    question_rounds: int = 0
    scene_revision: int = 0
    current_scene: FloorPlanScene | None = None
    last_render: FloorPlanRenderOutput | None = None


@dataclass(frozen=True, slots=True)
class FloorPlanIntakeDeps:
    """Dependency container for floor-plan intake graph execution."""

    output_dir: Path
    floor_plan_renderer: FloorPlanRenderCallable
    intake_decider: FloorPlanIntakeDeciderCallable
    max_question_rounds: int = 4


TIn = TypeVar("TIn", infer_variance=True)
TOut = TypeVar("TOut")
type IntakeStepContext[TIn] = StepContext[FloorPlanIntakeState, FloorPlanIntakeDeps, TIn]
type IntakeStepCallable[TIn, TOut] = Callable[[IntakeStepContext[TIn]], Awaitable[TOut]]
