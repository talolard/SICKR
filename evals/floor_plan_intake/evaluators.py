"""Custom evaluators for floor-plan intake conversation contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    EvaluatorOutput,
)

from evals.base import extract_logfire_tool_call_captures
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput


def _count_words(text: str) -> int:
    return len([word for word in text.replace("\n", " ").split(" ") if word.strip()])


@dataclass(slots=True)
class FinalOutputContractEvaluator(Evaluator[FloorPlanIntakeEvalInput, str, None]):
    """Check case-specific forbidden terms in the final user-facing response."""

    def evaluate(
        self,
        ctx: EvaluatorContext[FloorPlanIntakeEvalInput, str, None],
    ) -> EvaluatorOutput:
        """Evaluate one case against its forbidden final-response terms."""

        forbidden_terms = ctx.inputs.forbidden_response_terms
        if not forbidden_terms:
            return {}
        normalized_output = ctx.output.lower()
        violations = sorted({term for term in forbidden_terms if term.lower() in normalized_output})
        if not violations:
            return {
                "final_output_forbidden_terms": EvaluationReason(
                    value=True,
                    reason="Final output avoided all forbidden terms.",
                )
            }
        joined = ", ".join(f"`{term}`" for term in violations)
        return {
            "final_output_forbidden_terms": EvaluationReason(
                value=False,
                reason=f"Final output used forbidden term(s): {joined}.",
            )
        }


@dataclass(slots=True)
class ReplyWordCountEvaluator(Evaluator[FloorPlanIntakeEvalInput, str, None]):
    """Enforce the per-case maximum word count for concise first replies."""

    def evaluate(
        self,
        ctx: EvaluatorContext[FloorPlanIntakeEvalInput, str, None],
    ) -> EvaluatorOutput:
        """Evaluate whether the reply stayed within the configured word limit."""

        word_count = _count_words(ctx.output)
        max_word_count = ctx.inputs.max_word_count
        return {
            "reply_word_count": EvaluationReason(
                value=word_count <= max_word_count,
                reason=(
                    f"Reply used {word_count} words, within the {max_word_count}-word limit."
                    if word_count <= max_word_count
                    else (
                        f"Reply used {word_count} words, exceeding the {max_word_count}-word limit."
                    )
                ),
            )
        }


@dataclass(slots=True)
class ReplyQuestionCountEvaluator(Evaluator[FloorPlanIntakeEvalInput, str, None]):
    """Enforce the one-focused-question style from the floor-plan prompt."""

    def evaluate(
        self,
        ctx: EvaluatorContext[FloorPlanIntakeEvalInput, str, None],
    ) -> EvaluatorOutput:
        """Evaluate whether the reply stayed within the configured question limit."""

        question_count = ctx.output.count("?")
        max_question_count = ctx.inputs.max_question_count
        return {
            "reply_question_count": EvaluationReason(
                value=question_count <= max_question_count,
                reason=(
                    "Reply kept to the configured focused-question limit."
                    if question_count <= max_question_count
                    else (
                        f"Reply asked {question_count} questions, exceeding the "
                        f"{max_question_count}-question limit."
                    )
                ),
            )
        }


@dataclass(slots=True)
class RenderToolCallContractEvaluator(Evaluator[FloorPlanIntakeEvalInput, str, None]):
    """Require or forbid `render_floor_plan` calls for selected eval cases."""

    tool_name: str = "render_floor_plan"

    def evaluate(
        self,
        ctx: EvaluatorContext[FloorPlanIntakeEvalInput, str, None],
    ) -> EvaluatorOutput:
        """Evaluate whether `render_floor_plan` obeyed the case contract."""

        require_call = ctx.inputs.require_render_call
        forbid_call = ctx.inputs.forbid_render_call
        if not require_call and not forbid_call:
            return {}
        captures = extract_logfire_tool_call_captures(ctx.span_tree, tool_name=self.tool_name)
        if require_call and forbid_call:
            return {
                "render_call_contract": EvaluationReason(
                    value=False,
                    reason="Case cannot both require and forbid render tool calls.",
                )
            }
        if require_call:
            return {
                "render_call_contract": EvaluationReason(
                    value=bool(captures),
                    reason=(
                        "Render tool call observed."
                        if captures
                        else "Expected `render_floor_plan`, but no render tool call was captured."
                    ),
                )
            }
        return {
            "render_call_contract": EvaluationReason(
                value=not captures,
                reason=(
                    "No render tool call observed."
                    if not captures
                    else ("Render tool call was captured even though this case forbids rendering.")
                ),
            )
        }
