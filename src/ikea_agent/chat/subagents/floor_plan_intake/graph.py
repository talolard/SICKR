"""Graph construction and execution helpers for the floor-plan intake subagent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

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
    build_floor_plan_intake_decider,
    render_floor_plan_draft,
)
from ikea_agent.chat.subagents.floor_plan_intake.types import (
    FloorPlanIntakeDeciderCallable,
    FloorPlanIntakeDecision,
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


async def decide_floor_plan_intake_step(
    *,
    state: FloorPlanIntakeState,
    payload: FloorPlanIntakeInput,
    model_name: str | None = None,
) -> FloorPlanIntakeDecision:
    """Run the model-backed intake decider using this subagent's prompt instructions."""

    prompt_instructions = load_prompt(PROMPT_PATH)
    decider = build_floor_plan_intake_decider(
        prompt_instructions=prompt_instructions,
        model_name=model_name,
    )
    return await decider(state=state, payload=payload)


def build_floor_plan_intake_deps(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model_name: str | None = None,
) -> FloorPlanIntakeDeps:
    """Construct typed graph dependencies for one floor-plan intake run."""

    decider: FloorPlanIntakeDeciderCallable
    if model_name is None:

        async def decider(
            *,
            state: FloorPlanIntakeState,
            payload: FloorPlanIntakeInput,
        ) -> FloorPlanIntakeDecision:
            return await decide_floor_plan_intake_step(state=state, payload=payload)
    else:
        prompt_instructions = load_prompt(PROMPT_PATH)
        decider = cast(
            "FloorPlanIntakeDeciderCallable",
            build_floor_plan_intake_decider(
                prompt_instructions=prompt_instructions,
                model_name=model_name,
            ),
        )
    return FloorPlanIntakeDeps(
        output_dir=output_dir,
        floor_plan_renderer=render_floor_plan_draft,
        intake_decider=decider,
    )


async def run_floor_plan_intake(
    payload: FloorPlanIntakeInput,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model_name: str | None = None,
) -> FloorPlanIntakeOutcome:
    """Run one floor-plan intake turn and return a typed outcome."""

    _ = load_prompt(PROMPT_PATH)
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    graph = build_floor_plan_intake_graph()
    return await graph.run(
        state=FloorPlanIntakeState(),
        deps=build_floor_plan_intake_deps(output_dir=output_dir, model_name=model_name),
        inputs=payload,
    )


async def run_from_raw_input(
    raw_input: str,
    *,
    model_name: str | None = None,
) -> dict[str, object]:
    """Normalize raw input and execute one floor-plan intake run as JSON output."""

    normalized = parse_json_or_text(raw_input)
    payload = FloorPlanIntakeInput.model_validate(normalized)
    _ = load_prompt(PROMPT_PATH)
    await asyncio.to_thread(DEFAULT_OUTPUT_DIR.mkdir, parents=True, exist_ok=True)
    graph = build_floor_plan_intake_graph()
    outcome = await graph.run(
        state=FloorPlanIntakeState(),
        deps=build_floor_plan_intake_deps(output_dir=DEFAULT_OUTPUT_DIR, model_name=model_name),
        inputs=payload,
    )
    return outcome.model_dump(mode="json")
