"""Common helpers for subagent prompt loading and CLI input normalization."""

from __future__ import annotations

import json
from pathlib import Path


def read_prompt_markdown(prompt_path: Path) -> str:
    """Load markdown prompt content and fail loudly when missing."""

    if not prompt_path.exists():
        msg = f"Prompt file does not exist: {prompt_path}"
        raise FileNotFoundError(msg)
    return prompt_path.read_text(encoding="utf-8")


def instruction_text_from_prompt(prompt_path: Path) -> str:
    """Load prompt markdown and strip optional YAML front-matter."""

    raw = read_prompt_markdown(prompt_path).strip()
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            raw = raw[end + 3 :].lstrip("\n")
    return raw.strip()


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
