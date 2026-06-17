"""Shared helpers for authoring search eval dataset modules."""

from __future__ import annotations

from pydantic_evals import Case
from pydantic_evals.evaluators import Evaluator, LLMJudge

from evals.base import LogfireToolCallLLMJudge
from evals.search.types import SearchEvalInput

JUDGE_MODEL = "google-gla:gemini-2.5-flash"
SEARCH_RUBRIC = """\
You are evaluating whether a search agent produced high-quality `run_search_graph`
tool calls for a home-furnishing request.

The input contains:
- the user message
- `scenario_context`: optional prior-turn or continuation context
- `expected_search_attributes`: a list of must-address search requirements

The output contains:
- `tool_calls`: the captured `run_search_graph` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. Every expected search attribute is addressed by at least one query via semantic phrasing,
   structured filters, or exclusions.
2. The query set is solution-oriented rather than repetitive, covering the main product
   need plus useful adjacent or accessory searches where appropriate.
3. Hard constraints from the prompt are respected with reasonable filters or exclusions.
4. At least one query shows lateral or creative search reasoning beyond literal keyword
   repetition.

Grade FAIL if any expected attribute is entirely missing, if the query set is shallow or
repetitive, or if hard constraints such as size, price, or exclusions are ignored.
"""
BUNDLE_RUBRIC = """\
You are evaluating whether a search agent produced a high-quality `propose_bundle`
tool call after retrieval.

The input contains:
- the user message
- `scenario_context`: optional prior-turn or continuation context
- `expected_bundle_attributes`: bundle requirements that should appear in the proposal
- `forbidden_bundle_attributes`: bundle elements that should not appear
- `source_thread_id`: optional grounding reference for the originating conversation

The output contains:
- `tool_calls`: the captured `propose_bundle` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. At least one `propose_bundle` call is present when `expected_bundle_attributes` is non-empty.
2. Every expected bundle attribute is covered by the bundle title, line items, per-item reasons,
   quantities, notes, or the bundle response payload.
3. No forbidden bundle attribute appears in the proposed items, title, notes, or response payload.
4. The bundle reflects a coherent solution to the user's request rather than unrelated products.

Grade FAIL if the bundle omits required complementary products, includes forbidden products,
or shows no bundle call despite bundle-stage expectations.

When the expected or forbidden attributes concern sufficiency, quantity sanity, role
separation, or budget fit, judge concretely from counts, item types, reasons, and the
bundle response payload. Do not PASS based on superficial thematic similarity alone.
"""


def build_search_case_evaluators() -> tuple[Evaluator[SearchEvalInput, str, None], ...]:
    """Return the evaluators used for cases that judge search-tool quality."""

    return (
        LogfireToolCallLLMJudge(
            tool_name="run_search_graph",
            judge=LLMJudge(
                rubric=SEARCH_RUBRIC,
                model=JUDGE_MODEL,
                include_input=True,
                score=False,
                assertion={
                    "evaluation_name": "search_tool_call_quality",
                    "include_reason": True,
                },
            ),
        ),
    )


def build_bundle_case_evaluators() -> tuple[Evaluator[SearchEvalInput, str, None], ...]:
    """Return the extra evaluators used only for bundle-stage scenarios."""

    return (
        LogfireToolCallLLMJudge(
            tool_name="propose_bundle",
            judge=LLMJudge(
                rubric=BUNDLE_RUBRIC,
                model=JUDGE_MODEL,
                include_input=True,
                score=False,
                assertion={
                    "evaluation_name": "bundle_tool_call_quality",
                    "include_reason": True,
                },
            ),
        ),
    )


def build_case(
    name: str,
    user_message: str,
    search_attrs: list[str] | None = None,
    *,
    scenario_context: str | None = None,
    continue_from_history: bool = False,
    bundle_attrs: list[str] | None = None,
    forbidden_bundle_attrs: list[str] | None = None,
    forbidden_response_terms: list[str] | None = None,
    fixture_name: str | None = None,
    source_thread_id: str | None = None,
    require_search_call: bool | None = None,
    forbid_search_call: bool = False,
    require_bundle_call: bool = False,
    forbid_bundle_call: bool = False,
) -> Case[SearchEvalInput, str, None]:
    """Build one search eval case with optional bundle-stage expectations."""

    resolved_search_attrs = list(search_attrs or [])
    resolved_require_search_call = (
        bool(resolved_search_attrs) if require_search_call is None else require_search_call
    )
    case_evaluators: tuple[Evaluator[SearchEvalInput, str, None], ...] = ()
    if resolved_search_attrs:
        case_evaluators += build_search_case_evaluators()
    if bundle_attrs:
        case_evaluators += build_bundle_case_evaluators()
    return Case(
        name=name,
        inputs=SearchEvalInput(
            user_message=user_message,
            scenario_context=scenario_context,
            continue_from_history=continue_from_history,
            expected_search_attributes=resolved_search_attrs,
            expected_bundle_attributes=list(bundle_attrs or []),
            forbidden_bundle_attributes=list(forbidden_bundle_attrs or []),
            forbidden_response_terms=list(forbidden_response_terms or []),
            fixture_name=fixture_name,
            source_thread_id=source_thread_id,
            require_search_call=resolved_require_search_call,
            forbid_search_call=forbid_search_call,
            require_bundle_call=require_bundle_call,
            forbid_bundle_call=forbid_bundle_call,
        ),
        evaluators=case_evaluators,
    )


__all__ = [
    "BUNDLE_RUBRIC",
    "JUDGE_MODEL",
    "SEARCH_RUBRIC",
    "build_bundle_case_evaluators",
    "build_case",
    "build_search_case_evaluators",
]
