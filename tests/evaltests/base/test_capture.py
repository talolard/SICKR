from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from evals.base.capture import (
    extract_logfire_tool_call_captures,
    extract_message_tool_call_captures,
)
from pydantic_ai.messages import ModelResponse, ToolCallPart
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
        return self.spans


def test_extract_logfire_tool_call_captures_parses_tool_arguments_json() -> None:
    span_tree = cast(
        "SpanTree",
        _FakeSpanTree(
            spans=[
                _FakeSpan(
                    attributes={
                        "gen_ai.tool.name": "run_search_graph",
                        "gen_ai.tool.call.id": "tool-call-1",
                        "tool_arguments": '{"queries":[{"semantic_query":"small desk"}]}',
                        "tool_response": '{"queries":[]}',
                    }
                ),
                _FakeSpan(
                    attributes={
                        "gen_ai.tool.name": "other_tool",
                        "tool_arguments": '{"value": 1}',
                    }
                ),
            ]
        ),
    )

    captures = extract_logfire_tool_call_captures(
        span_tree,
        tool_name="run_search_graph",
    )

    assert len(captures) == 1
    assert captures[0].tool_name == "run_search_graph"
    assert captures[0].tool_call_id == "tool-call-1"
    assert captures[0].args == {"queries": [{"semantic_query": "small desk"}]}
    assert captures[0].response == {"queries": []}


def test_extract_message_tool_call_captures_reads_model_responses() -> None:
    messages = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="run_search_graph",
                    tool_call_id="tool-call-2",
                    args={"queries": [{"semantic_query": "outdoor desk"}]},
                )
            ]
        )
    ]

    captures = extract_message_tool_call_captures(messages, tool_name="run_search_graph")

    assert len(captures) == 1
    assert captures[0].tool_name == "run_search_graph"
    assert captures[0].tool_call_id == "tool-call-2"
    assert captures[0].args == {"queries": [{"semantic_query": "outdoor desk"}]}
