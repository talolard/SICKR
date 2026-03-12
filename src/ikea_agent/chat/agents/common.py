"""Common helpers for agent prompt loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentPrompt:
    """Prompt helper for loading markdown and instruction text from a file path."""

    path: Path

    def read_markdown(self) -> str:
        """Load prompt markdown content and fail loudly when missing."""

        if not self.path.exists():
            msg = f"Prompt file does not exist: {self.path}"
            raise FileNotFoundError(msg)
        return self.path.read_text(encoding="utf-8")

    def instruction_text(self) -> str:
        """Load prompt markdown and strip optional YAML front-matter."""

        raw = self.read_markdown().strip()
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                raw = raw[end + 3 :].lstrip("\n")
        return raw.strip()
