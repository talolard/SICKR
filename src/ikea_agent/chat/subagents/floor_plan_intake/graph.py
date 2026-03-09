"""Graph construction and execution helpers for the floor-plan intake subagent."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_graph.beta import Graph, GraphBuilder

from ikea_agent.chat.subagents.common import load_prompt, parse_json_or_text
from ikea_agent.chat.subagents.floor_plan_intake.nodes import (
    RouteSignal,
    ask_constraints_outcome,
    ask_dimensions_outcome,
    ask_orientation_outcome,
    complete_outcome,
    render_draft_outcome,
    route_turn,
    unsupported_image_outcome,
)
from ikea_agent.chat.subagents.floor_plan_intake.tools import (
    decide_floor_plan_intake_step,
    render_floor_plan_draft,
)
from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDeps,
    FloorPlanIntakeInput,
    FloorPlanIntakeOutcome,
    FloorPlanIntakeState,
)

PROMPT_PATH = Path(__file__).with_name("prompt.md")
DEFAULT_OUTPUT_DIR = Path("artifacts/floor_plans/subagents/floor_plan_intake")


def build_floor_plan_intake_graph() -> Graph[
    FloorPlanIntakeState,
    FloorPlanIntakeDeps,
    FloorPlanIntakeInput,
    FloorPlanIntakeOutcome,
]:
    """Build the floor-plan intake graph using beta GraphBuilder steps and edges."""

    builder = GraphBuilder[
        FloorPlanIntakeState,
        FloorPlanIntakeDeps,
        FloorPlanIntakeInput,
        FloorPlanIntakeOutcome,
    ]()

    route_step = builder.step(route_turn, node_id="route_turn")
    unsupported_step = builder.step(unsupported_image_outcome, node_id="unsupported_image_outcome")
    complete_step = builder.step(complete_outcome, node_id="complete_outcome")
    ask_dimensions_step = builder.step(ask_dimensions_outcome, node_id="ask_dimensions_outcome")
    ask_orientation_step = builder.step(ask_orientation_outcome, node_id="ask_orientation_outcome")
    ask_constraints_step = builder.step(ask_constraints_outcome, node_id="ask_constraints_outcome")
    render_step = builder.step(render_draft_outcome, node_id="render_draft_outcome")

    route_decision = (
        builder.decision(note="Route intake turn to one terminal step")
        .branch(
            builder.match(RouteSignal, matches=lambda signal: signal.kind == "unsupported_image")
            .label("unsupported_image")
            .to(unsupported_step)
        )
        .branch(
            builder.match(RouteSignal, matches=lambda signal: signal.kind == "complete")
            .label("complete")
            .to(complete_step)
        )
        .branch(
            builder.match(RouteSignal, matches=lambda signal: signal.kind == "ask_dimensions")
            .label("ask_dimensions")
            .to(ask_dimensions_step)
        )
        .branch(
            builder.match(RouteSignal, matches=lambda signal: signal.kind == "ask_orientation")
            .label("ask_orientation")
            .to(ask_orientation_step)
        )
        .branch(
            builder.match(RouteSignal, matches=lambda signal: signal.kind == "ask_constraints")
            .label("ask_constraints")
            .to(ask_constraints_step)
        )
        .branch(builder.match(RouteSignal).label("render").to(render_step))
    )

    builder.add(
        builder.edge_from(builder.start_node).to(route_step),
        builder.edge_from(route_step).to(route_decision),
        builder.edge_from(unsupported_step).to(builder.end_node),
        builder.edge_from(complete_step).to(builder.end_node),
        builder.edge_from(ask_dimensions_step).to(builder.end_node),
        builder.edge_from(ask_orientation_step).to(builder.end_node),
        builder.edge_from(ask_constraints_step).to(builder.end_node),
        builder.edge_from(render_step).to(builder.end_node),
    )
    return builder.build()


async def run_floor_plan_intake(
    payload: FloorPlanIntakeInput,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> FloorPlanIntakeOutcome:
    """Run one floor-plan intake turn and return a typed outcome."""

    _ = load_prompt(PROMPT_PATH)
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    graph = build_floor_plan_intake_graph()
    return await graph.run(
        state=FloorPlanIntakeState(),
        deps=FloorPlanIntakeDeps(
            output_dir=output_dir,
            floor_plan_renderer=render_floor_plan_draft,
            intake_decider=decide_floor_plan_intake_step,
        ),
        inputs=payload,
    )


async def run_from_raw_input(raw_input: str) -> dict[str, object]:
    """CLI-facing adapter that normalizes raw input and returns JSON-safe output."""

    normalized = parse_json_or_text(raw_input)
    payload = FloorPlanIntakeInput.model_validate(normalized)
    outcome = await run_floor_plan_intake(payload)
    return outcome.model_dump(mode="json")
