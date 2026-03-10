"""Class-based subgraph agent for floor-plan intake."""

from __future__ import annotations

from pathlib import Path

from pydantic_graph.beta import Graph

from ikea_agent.chat.subagents.base import SubgraphAgent
from ikea_agent.chat.subagents.floor_plan_intake.graph import (
    DEFAULT_OUTPUT_DIR,
    build_floor_plan_intake_deps,
    build_floor_plan_intake_graph,
)
from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDeps,
    FloorPlanIntakeInput,
    FloorPlanIntakeOutcome,
    FloorPlanIntakeState,
)


class FloorPlannerSubgraphAgent(
    SubgraphAgent[
        FloorPlanIntakeState,
        FloorPlanIntakeDeps,
        FloorPlanIntakeInput,
        FloorPlanIntakeOutcome,
    ]
):
    """Graph-backed floor-plan intake subagent with explicit prompt/tool contract."""

    subagent_name = "floor_plan_intake"
    description = "Collect initial room architecture and render iterative floor-plan drafts."
    prompt_path = Path(__file__).with_name("prompt.md")
    tool_names = ("decide_floor_plan_intake_step", "render_floor_plan_draft")
    notes = (
        "Runs an iterative intake loop and emits a floor-plan scene compatible with the "
        "repository floorplanner renderer."
    )

    @classmethod
    def build_graph(
        cls,
    ) -> Graph[
        FloorPlanIntakeState,
        FloorPlanIntakeDeps,
        FloorPlanIntakeInput,
        FloorPlanIntakeOutcome,
    ]:
        """Build the floor-plan intake graph instance."""

        return build_floor_plan_intake_graph()

    @classmethod
    def build_state(cls) -> FloorPlanIntakeState:
        """Return a fresh state object for one graph turn."""

        return FloorPlanIntakeState()

    @classmethod
    def build_turn_notes(
        cls,
        *,
        user_message: str,
        output: object,
        state: FloorPlanIntakeState,
    ) -> list[str]:
        """Capture high-signal floor-plan notes that don't fit typed state fields."""

        _ = user_message
        notes: list[str] = []
        if state.height_assumed_default:
            notes.append("Used default room height assumption: 280 cm.")
        if state.fixed_constraints:
            notes.append(
                "Captured fixed constraints: "
                + ", ".join(sorted(set(state.fixed_constraints)))
                + "."
            )
        if isinstance(output, FloorPlanIntakeOutcome) and output.status == "rendered_draft":
            notes.append(f"Rendered draft revision {output.scene_revision}.")
        return notes

    @classmethod
    def build_deps(cls, *, model_name: str) -> FloorPlanIntakeDeps:
        """Build typed dependencies for one graph turn."""

        return build_floor_plan_intake_deps(
            output_dir=DEFAULT_OUTPUT_DIR,
            model_name=model_name,
        )

    @classmethod
    def parse_user_input(cls, user_message: str) -> FloorPlanIntakeInput:
        """Convert latest user text into the typed graph input payload."""

        return FloorPlanIntakeInput(user_message=user_message)

    @classmethod
    def output_to_json(cls, output: object) -> dict[str, object]:
        """Serialize known floor-plan outcomes; fall back to generic conversion."""

        if isinstance(output, FloorPlanIntakeOutcome):
            return output.model_dump(mode="json")
        return super().output_to_json(output)


__all__ = ["FloorPlannerSubgraphAgent"]
