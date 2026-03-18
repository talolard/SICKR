from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from evals.floor_plan_intake.evaluators import (
    FinalOutputContractEvaluator,
    RenderToolCallContractEvaluator,
    ReplyQuestionCountEvaluator,
    ReplyWordCountEvaluator,
)
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput
from pydantic_evals.evaluators import EvaluationReason, EvaluatorContext
from pydantic_evals.otel import SpanTree


@dataclass(frozen=True, slots=True)
class _FakeSpan:
    attributes: dict[str, object]


@dataclass(frozen=True, slots=True)
class _FakeSpanTree:
    spans: list[_FakeSpan]

    def find(self, query: dict[str, object]) -> list[_FakeSpan]:
        if query.get("name_equals") != "running tool":
            return []
        tool_name = None
        has_attributes = query.get("has_attributes")
        if isinstance(has_attributes, dict):
            tool_name = has_attributes.get("gen_ai.tool.name")
        if tool_name is None:
            return self.spans
        return [span for span in self.spans if span.attributes.get("gen_ai.tool.name") == tool_name]


def _context(
    *,
    inputs: FloorPlanIntakeEvalInput,
    output: str,
    spans: list[_FakeSpan] | None = None,
) -> EvaluatorContext[FloorPlanIntakeEvalInput, str, None]:
    return EvaluatorContext(
        name="case",
        inputs=inputs,
        metadata=None,
        expected_output=None,
        output=output,
        duration=0.1,
        _span_tree=cast("SpanTree", _FakeSpanTree(spans=spans or [])),
        attributes={},
        metrics={},
    )


def test_final_output_contract_evaluator_flags_forbidden_term() -> None:
    evaluator = FinalOutputContractEvaluator()
    ctx = _context(
        inputs=FloorPlanIntakeEvalInput(
            user_message="Small bathroom, no measurements yet.",
            forbidden_response_terms=["What are the dimensions?"],
        ),
        output="What are the dimensions? We can start there.",
    )

    result = cast("dict[str, EvaluationReason]", evaluator.evaluate(ctx))

    assert result["final_output_forbidden_terms"].value is False
    reason = result["final_output_forbidden_terms"].reason
    assert reason is not None
    assert "What are the dimensions?" in reason


def test_reply_word_count_evaluator_fails_long_reply() -> None:
    evaluator = ReplyWordCountEvaluator()
    ctx = _context(
        inputs=FloorPlanIntakeEvalInput(
            user_message="Hallway.",
            max_word_count=5,
        ),
        output="This reply is definitely too long for the configured limit.",
    )

    result = cast("dict[str, EvaluationReason]", evaluator.evaluate(ctx))

    assert result["reply_word_count"].value is False


def test_reply_question_count_evaluator_fails_multiple_questions() -> None:
    evaluator = ReplyQuestionCountEvaluator()
    ctx = _context(
        inputs=FloorPlanIntakeEvalInput(
            user_message="Living room.",
            max_question_count=1,
        ),
        output="Where is the entrance? How many windows are there?",
    )

    result = cast("dict[str, EvaluationReason]", evaluator.evaluate(ctx))

    assert result["reply_question_count"].value is False
    reason = result["reply_question_count"].reason
    assert reason is not None
    assert "2 questions" in reason


def test_render_tool_call_contract_evaluator_requires_render_when_configured() -> None:
    evaluator = RenderToolCallContractEvaluator()
    ctx = _context(
        inputs=FloorPlanIntakeEvalInput(
            user_message="Let's move on to a draft.",
            require_render_call=True,
        ),
        output="Here is my summary before drafting.",
    )

    result = cast("dict[str, EvaluationReason]", evaluator.evaluate(ctx))

    assert result["render_call_contract"].value is False
    reason = result["render_call_contract"].reason
    assert reason is not None
    assert "Expected `render_floor_plan`" in reason


def test_render_tool_call_contract_evaluator_forbids_render_when_configured() -> None:
    evaluator = RenderToolCallContractEvaluator()
    ctx = _context(
        inputs=FloorPlanIntakeEvalInput(
            user_message="Just orient me first.",
            forbid_render_call=True,
        ),
        output="Let's anchor the walls first.",
        spans=[
            _FakeSpan(
                attributes={
                    "gen_ai.tool.name": "render_floor_plan",
                    "tool_arguments": '{"scene":{"scene_level":"baseline"}}',
                }
            )
        ],
    )

    result = cast("dict[str, EvaluationReason]", evaluator.evaluate(ctx))

    assert result["render_call_contract"].value is False
    reason = result["render_call_contract"].reason
    assert reason is not None
    assert "forbids rendering" in reason
