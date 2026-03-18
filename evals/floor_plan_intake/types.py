"""Typed inputs and capture payloads for floor-plan intake evals."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from evals.base import MessageToolCallCapture, MessageToolReturnCapture


@dataclass(frozen=True, slots=True)
class FloorPlanIntakeEvalInput:
    """One floor-plan intake eval case with explicit opening and render contracts."""

    user_message: str
    expected_response_attributes: list[str] = field(default_factory=list)
    expected_render_attributes: list[str] = field(default_factory=list)
    forbidden_response_terms: list[str] = field(default_factory=list)
    max_word_count: int = 180
    max_question_count: int = 1
    require_render_call: bool = False
    forbid_render_call: bool = False
    source_trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class FloorPlanIntakeEvalRunCapture:
    """Serializable capture payload for fixture authoring and review."""

    final_output: str
    message_tool_calls: list[MessageToolCallCapture]
    message_tool_returns: list[MessageToolReturnCapture]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for the capture CLI."""

        return {
            "final_output": self.final_output,
            "message_tool_calls": [asdict(capture) for capture in self.message_tool_calls],
            "message_tool_returns": [asdict(capture) for capture in self.message_tool_returns],
        }
