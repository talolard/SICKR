"""Helpers for extracting tool call payloads from traces and messages."""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_evals.otel import SpanTree

from evals.base.types import (
    LogfireToolCallCapture,
    MessageToolCallCapture,
    MessageToolReturnCapture,
)


def _coerce_json_object(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    if isinstance(raw, str):
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return {str(key): value for key, value in loaded.items()}
    return {}


def _coerce_json_value(raw: object) -> object | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def extract_logfire_tool_call_captures(
    span_tree: SpanTree,
    *,
    tool_name: str | None = None,
) -> list[LogfireToolCallCapture]:
    """Return Logfire-backed tool call captures from an eval span tree."""

    captures: list[LogfireToolCallCapture] = []
    for span in span_tree.find({"name_equals": "running tool"}):
        current_tool_name = span.attributes.get("gen_ai.tool.name")
        if not isinstance(current_tool_name, str):
            continue
        if tool_name is not None and current_tool_name != tool_name:
            continue
        captures.append(
            LogfireToolCallCapture(
                kind="logfire_tool_call",
                tool_name=current_tool_name,
                tool_call_id=(
                    str(span.attributes["gen_ai.tool.call.id"])
                    if "gen_ai.tool.call.id" in span.attributes
                    else None
                ),
                args=_coerce_json_object(span.attributes.get("tool_arguments")),
                response=_coerce_json_value(span.attributes.get("tool_response")),
            )
        )
    return captures


def extract_message_tool_call_captures(
    messages: Sequence[object],
    *,
    tool_name: str | None = None,
) -> list[MessageToolCallCapture]:
    """Return tool calls extracted from PydanticAI message history."""

    captures: list[MessageToolCallCapture] = []
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        for part in message.parts:
            if not isinstance(part, ToolCallPart):
                continue
            if tool_name is not None and part.tool_name != tool_name:
                continue
            captures.append(
                MessageToolCallCapture(
                    kind="message_tool_call",
                    tool_name=part.tool_name,
                    tool_call_id=part.tool_call_id,
                    args=_coerce_json_object(part.args),
                )
            )
    return captures


def extract_message_tool_return_captures(
    messages: Sequence[object],
    *,
    tool_name: str | None = None,
) -> list[MessageToolReturnCapture]:
    """Return tool returns extracted from PydanticAI message history."""

    captures: list[MessageToolReturnCapture] = []
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if not isinstance(part, ToolReturnPart):
                continue
            if tool_name is not None and part.tool_name != tool_name:
                continue
            captures.append(
                MessageToolReturnCapture(
                    kind="message_tool_return",
                    tool_name=part.tool_name,
                    tool_call_id=part.tool_call_id,
                    content=_coerce_json_value(part.content),
                    outcome=part.outcome,
                )
            )
    return captures
