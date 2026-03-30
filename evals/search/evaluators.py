"""Custom evaluators for search-agent conversation contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    EvaluatorOutput,
)

from evals.base import extract_logfire_tool_call_captures
from evals.search.types import SearchEvalInput


@dataclass(slots=True)
class SearchToolCallContractEvaluator(Evaluator[SearchEvalInput, str, None]):
    """Require or forbid `run_search_graph` calls for selected eval cases."""

    tool_name: str = "run_search_graph"

    def evaluate(self, ctx: EvaluatorContext[SearchEvalInput, str, None]) -> EvaluatorOutput:
        """Evaluate whether `run_search_graph` obeyed the case contract."""

        require_call = ctx.inputs.require_search_call
        forbid_call = ctx.inputs.forbid_search_call
        if not require_call and not forbid_call:
            return {}
        captures = extract_logfire_tool_call_captures(ctx.span_tree, tool_name=self.tool_name)
        if require_call and forbid_call:
            return {
                "search_call_contract": EvaluationReason(
                    value=False,
                    reason="Case cannot both require and forbid search calls.",
                )
            }
        if require_call:
            return {
                "search_call_contract": EvaluationReason(
                    value=bool(captures),
                    reason=(
                        "Search call observed."
                        if captures
                        else "Expected `run_search_graph`, but no search tool call was captured."
                    ),
                )
            }
        return {
            "search_call_contract": EvaluationReason(
                value=not captures,
                reason=(
                    "No search call observed."
                    if not captures
                    else "Search tool call was captured even though this case forbids search."
                ),
            )
        }


@dataclass(slots=True)
class FinalOutputContractEvaluator(Evaluator[SearchEvalInput, str, None]):
    """Check case-specific forbidden terms in the final user-facing response."""

    def evaluate(self, ctx: EvaluatorContext[SearchEvalInput, str, None]) -> EvaluatorOutput:
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
class BundleToolCallContractEvaluator(Evaluator[SearchEvalInput, str, None]):
    """Require or forbid `propose_bundle` calls for selected eval cases."""

    tool_name: str = "propose_bundle"

    def evaluate(self, ctx: EvaluatorContext[SearchEvalInput, str, None]) -> EvaluatorOutput:
        """Evaluate whether `propose_bundle` obeyed the case contract."""

        require_call = ctx.inputs.require_bundle_call
        forbid_call = ctx.inputs.forbid_bundle_call
        if not require_call and not forbid_call:
            return {}
        captures = extract_logfire_tool_call_captures(ctx.span_tree, tool_name=self.tool_name)
        if require_call and forbid_call:
            return {
                "bundle_call_contract": EvaluationReason(
                    value=False,
                    reason="Case cannot both require and forbid bundle calls.",
                )
            }
        if require_call:
            return {
                "bundle_call_contract": EvaluationReason(
                    value=bool(captures),
                    reason=(
                        "Bundle call observed."
                        if captures
                        else "Expected `propose_bundle`, but no bundle tool call was captured."
                    ),
                )
            }
        return {
            "bundle_call_contract": EvaluationReason(
                value=not captures,
                reason=(
                    "No bundle call observed."
                    if not captures
                    else "Bundle tool call was captured even though this case forbids bundling."
                ),
            )
        }
