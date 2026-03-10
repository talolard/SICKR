"""Common helpers for agent prompt loading and CLI input normalization."""

from __future__ import annotations

import json
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


def read_prompt_markdown(prompt_path: Path) -> str:
    """Load markdown prompt content and fail loudly when missing."""

    return AgentPrompt(prompt_path).read_markdown()


def instruction_text_from_prompt(prompt_path: Path) -> str:
    """Load prompt markdown and strip optional YAML front-matter."""

    return AgentPrompt(prompt_path).instruction_text()


def load_prompt(prompt_path: Path) -> str:
    """Backward-compatible alias for prompt markdown loading."""

    return read_prompt_markdown(prompt_path)


def parse_json_or_text(raw_input: str) -> dict[str, object]:
    """Parse raw CLI input as JSON object when possible, otherwise wrap as text."""

    stripped = raw_input.strip()
    if not stripped:
        return {"user_message": ""}
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"user_message": raw_input}

    if isinstance(parsed, dict):
        return parsed
    return {"user_message": raw_input}
