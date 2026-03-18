"""Shared helpers for authoring floor-plan intake eval dataset modules."""

from __future__ import annotations

from pydantic_evals import Case
from pydantic_evals.evaluators import Evaluator, HasMatchingSpan, LLMJudge

from evals.base import LogfireToolCallLLMJudge
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput

JUDGE_MODEL = "google-gla:gemini-2.5-flash"
RENDER_FLOOR_PLAN_SPAN_QUERY = {
    "name_equals": "running tool",
    "has_attributes": {"gen_ai.tool.name": "render_floor_plan"},
}
OPENING_RUBRIC = """\
You are evaluating whether a floor-plan intake agent gave a strong, concise
user-facing reply for an early room-intake turn.

The input contains:
- the user message
- `expected_response_attributes`: behaviors the reply should demonstrate
- `max_word_count` and `max_question_count`: hard style limits

The output contains:
- the final user-facing text

Grade PASS only if all of the following hold:
1. Every expected response attribute is satisfied in substance.
2. The reply is orientation-first rather than immediately demanding dimensions.
3. The reply keeps the focus on room shell, openings, and fixed features.
4. The reply feels concise and practical instead of dumping a checklist.

Grade FAIL if the reply skips orientation, asks a broad multi-part interrogation,
switches prematurely to furniture/layout, or ignores explicit reply constraints.
"""
RENDER_RUBRIC = """\
You are evaluating whether a floor-plan intake agent produced a high-quality
`render_floor_plan` tool call once the user had provided enough room-shell detail
or explicitly said to move on to a first draft.

The input contains:
- the user message
- `expected_render_attributes`: render expectations that should appear in the tool call

The output contains:
- `tool_calls`: the captured `render_floor_plan` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. At least one `render_floor_plan` call is present when render expectations exist.
2. The tool call reflects the described room shell with coherent wall/opening geometry.
3. The render payload is baseline-intake appropriate rather than inventing unrelated detail.
4. The final output frames the result as a draft, surfaces assumptions, and asks for correction.

Grade FAIL if the agent does not render despite enough information, invents major room facts,
or produces a draft that is inconsistent with the user's wall-by-wall description.
"""


def build_render_case_evaluators() -> tuple[Evaluator[FloorPlanIntakeEvalInput, str, None], ...]:
    """Return the extra evaluators used only for render-stage scenarios."""

    return (
        HasMatchingSpan(
            query=RENDER_FLOOR_PLAN_SPAN_QUERY,
            evaluation_name="called_render_floor_plan",
        ),
        LogfireToolCallLLMJudge(
            tool_name="render_floor_plan",
            judge=LLMJudge(
                rubric=RENDER_RUBRIC,
                model=JUDGE_MODEL,
                include_input=True,
                score=False,
                assertion={
                    "evaluation_name": "render_floor_plan_quality",
                    "include_reason": True,
                },
            ),
        ),
    )


def build_case(
    name: str,
    user_message: str,
    response_attrs: list[str],
    *,
    render_attrs: list[str] | None = None,
    forbidden_response_terms: list[str] | None = None,
    max_word_count: int = 180,
    max_question_count: int = 1,
    require_render_call: bool = False,
    forbid_render_call: bool = False,
    source_trace_id: str | None = None,
) -> Case[FloorPlanIntakeEvalInput, str, None]:
    """Build one floor-plan intake eval case with optional render expectations."""

    case_evaluators: tuple[Evaluator[FloorPlanIntakeEvalInput, str, None], ...] = ()
    if render_attrs or require_render_call or forbid_render_call:
        case_evaluators = build_render_case_evaluators()
    return Case(
        name=name,
        inputs=FloorPlanIntakeEvalInput(
            user_message=user_message,
            expected_response_attributes=list(response_attrs),
            expected_render_attributes=list(render_attrs or []),
            forbidden_response_terms=list(forbidden_response_terms or []),
            max_word_count=max_word_count,
            max_question_count=max_question_count,
            require_render_call=require_render_call,
            forbid_render_call=forbid_render_call,
            source_trace_id=source_trace_id,
        ),
        evaluators=case_evaluators,
    )


__all__ = [
    "JUDGE_MODEL",
    "OPENING_RUBRIC",
    "RENDER_FLOOR_PLAN_SPAN_QUERY",
    "RENDER_RUBRIC",
    "build_case",
    "build_render_case_evaluators",
]
