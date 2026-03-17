"""Shared typed contracts for eval harnesses and capture records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeGuard


@dataclass(frozen=True, slots=True)
class LogfireToolCallCapture:
    """One tool call captured from native PydanticAI/Logfire spans."""

    kind: Literal["logfire_tool_call"]
    tool_name: str
    args: dict[str, object]
    tool_call_id: str | None = None
    response: object | None = None


@dataclass(frozen=True, slots=True)
class MessageToolCallCapture:
    """One tool call captured from PydanticAI message history."""

    kind: Literal["message_tool_call"]
    tool_name: str
    args: dict[str, object]
    tool_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class MessageToolReturnCapture:
    """One tool return captured from PydanticAI message history."""

    kind: Literal["message_tool_return"]
    tool_name: str
    content: object | None
    outcome: Literal["success", "failed", "denied"]
    tool_call_id: str | None = None


ToolCallCapture = LogfireToolCallCapture | MessageToolCallCapture


def is_logfire_tool_call_capture(value: ToolCallCapture) -> TypeGuard[LogfireToolCallCapture]:
    """Return True when the capture originated from Logfire spans."""

    return value.kind == "logfire_tool_call"


@dataclass(frozen=True, slots=True)
class ToolCallJudgeOutput:
    """Synthetic grading surface used by span-backed eval judges."""

    tool_calls: list[ToolCallCapture]
    final_output: object
