from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from evals.search.evaluators import (
    BundleToolCallContractEvaluator,
    FinalOutputContractEvaluator,
    SearchToolCallContractEvaluator,
)
from evals.search.fixtures import SEARCH_EVAL_FIXTURES
from evals.search.types import SearchEvalInput
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
    inputs: SearchEvalInput,
    output: str,
    spans: list[_FakeSpan] | None = None,
) -> EvaluatorContext[SearchEvalInput, str, None]:
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
        inputs=SearchEvalInput(
            user_message="Help me find hallway lighting.",
            forbidden_response_terms=["bundle"],
        ),
        output="Here is a bundle of ideas for your hallway.",
    )

    result = cast(
        "dict[str, EvaluationReason]",
        evaluator.evaluate(ctx),
    )

    assert result["final_output_forbidden_terms"].value is False
    reason = result["final_output_forbidden_terms"].reason
    assert reason is not None
    assert "bundle" in reason


def test_bundle_tool_call_contract_evaluator_requires_bundle_when_configured() -> None:
    evaluator = BundleToolCallContractEvaluator()
    ctx = _context(
        inputs=SearchEvalInput(
            user_message="Build me a renter-safe gallery wall.",
            require_bundle_call=True,
        ),
        output="I found a few options.",
    )

    result = cast(
        "dict[str, EvaluationReason]",
        evaluator.evaluate(ctx),
    )

    assert result["bundle_call_contract"].value is False
    reason = result["bundle_call_contract"].reason
    assert reason is not None
    assert "Expected `propose_bundle`" in reason


def test_search_tool_call_contract_evaluator_requires_search_when_configured() -> None:
    evaluator = SearchToolCallContractEvaluator()
    ctx = _context(
        inputs=SearchEvalInput(
            user_message="Find a few compact desks.",
            require_search_call=True,
        ),
        output="I found some desks.",
    )

    result = cast(
        "dict[str, EvaluationReason]",
        evaluator.evaluate(ctx),
    )

    assert result["search_call_contract"].value is False
    reason = result["search_call_contract"].reason
    assert reason is not None
    assert "Expected `run_search_graph`" in reason


def test_search_tool_call_contract_evaluator_forbids_search_when_configured() -> None:
    evaluator = SearchToolCallContractEvaluator()
    ctx = _context(
        inputs=SearchEvalInput(
            user_message="Formalize the already grounded bundle.",
            forbid_search_call=True,
        ),
        output="The bundle is ready.",
        spans=[
            _FakeSpan(
                attributes={
                    "gen_ai.tool.name": "run_search_graph",
                    "tool_arguments": '{"queries":[{"semantic_query":"desk"}]}',
                }
            )
        ],
    )

    result = cast(
        "dict[str, EvaluationReason]",
        evaluator.evaluate(ctx),
    )

    assert result["search_call_contract"].value is False
    reason = result["search_call_contract"].reason
    assert reason is not None
    assert "forbids search" in reason


def test_bundle_tool_call_contract_evaluator_forbids_bundle_when_configured() -> None:
    evaluator = BundleToolCallContractEvaluator()
    ctx = _context(
        inputs=SearchEvalInput(
            user_message="Only tell me if nothing matches.",
            forbid_bundle_call=True,
        ),
        output="No exact match yet.",
        spans=[
            _FakeSpan(
                attributes={
                    "gen_ai.tool.name": "propose_bundle",
                    "tool_arguments": '{"items":[]}',
                }
            )
        ],
    )

    result = cast(
        "dict[str, EvaluationReason]",
        evaluator.evaluate(ctx),
    )

    assert result["bundle_call_contract"].value is False
    reason = result["bundle_call_contract"].reason
    assert reason is not None
    assert "forbids bundling" in reason


def test_search_eval_fixture_resolve_results_uses_seeded_products() -> None:
    fixture = SEARCH_EVAL_FIXTURES["hallway_complementary_seed"]

    results = fixture.resolve_results("portable hallway lighting with a shelf")

    assert len(results) >= 3
    assert any(result.product_name == "LÄNSPORT portable lamp" for result in results)
