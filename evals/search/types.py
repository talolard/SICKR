"""Typed inputs and capture payloads for search-agent evals."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from evals.base import MessageToolCallCapture, MessageToolReturnCapture
from ikea_agent.shared.types import BundleProposalToolResult


@dataclass(frozen=True, slots=True)
class SearchEvalInput:
    """One search-eval case with explicit search, bundle, and response contracts."""

    user_message: str
    expected_search_attributes: list[str] = field(default_factory=list)
    expected_bundle_attributes: list[str] = field(default_factory=list)
    forbidden_bundle_attributes: list[str] = field(default_factory=list)
    forbidden_response_terms: list[str] = field(default_factory=list)
    fixture_name: str | None = None
    source_thread_id: str | None = None
    require_bundle_call: bool = False
    forbid_bundle_call: bool = False


@dataclass(frozen=True, slots=True)
class SearchEvalRunCapture:
    """Serializable capture payload for fixture authoring and review."""

    final_output: str
    message_tool_calls: list[MessageToolCallCapture]
    message_tool_returns: list[MessageToolReturnCapture]
    bundle_proposals: list[BundleProposalToolResult]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for the capture CLI."""

        return {
            "final_output": self.final_output,
            "message_tool_calls": [asdict(capture) for capture in self.message_tool_calls],
            "message_tool_returns": [asdict(capture) for capture in self.message_tool_returns],
            "bundle_proposals": [
                proposal.model_dump(mode="json") for proposal in self.bundle_proposals
            ],
        }
