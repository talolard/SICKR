"""Shared contracts for tool implementations and agent-facing wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """Result envelope shared by all tools exposed through the bridge.

    The intent is to keep transport shape consistent regardless of whether a tool is
    called directly from Python code or through a decorated agent function.
    """

    tool_name: str
    success: bool
    message: str
    output_path: Path | None = None
    metadata: dict[str, object] | None = None
    errors: tuple[str, ...] = ()


class ToolProtocol(Protocol):
    """Protocol implemented by concrete domain tools."""

    def run(self, payload: object) -> ToolExecutionResult:
        """Execute one tool operation and return a normalized result envelope."""
