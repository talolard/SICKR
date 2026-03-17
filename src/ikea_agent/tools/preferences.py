"""Shared models and helpers for explicit thread preference capture tools.

Agents use this path when a user reveals a durable fact, constraint, or taste
signal that should shape later turns. The agent supplies a compact key plus a
one- or two-line summary, and the helper maps that note into the persisted
thread-memory record used by later agent runs.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from ikea_agent.shared.types import (
    RevealedPreferenceKind,
    RevealedPreferenceMemory,
    RevealedPreferenceMemoryInput,
)

_KEY_PATTERN = re.compile(r"[^a-z0-9]+")


class PreferenceNoteInput(BaseModel):
    """Compact durable preference note authored by an agent."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    kind: RevealedPreferenceKind
    summary: str = Field(min_length=1)
    source: str | None = None


class PreferenceNoteResult(BaseModel):
    """Result returned after storing one durable thread preference note."""

    model_config = ConfigDict(extra="forbid")

    message: str
    memory: RevealedPreferenceMemory


def note_to_memory_input(note: PreferenceNoteInput) -> RevealedPreferenceMemoryInput:
    """Normalize one explicit note into the persisted memory input shape."""

    normalized_key = _normalize_note_key(note.key)
    summary = note.summary.strip()
    return RevealedPreferenceMemoryInput(
        signal_key="agent_note",
        kind=note.kind,
        value=normalized_key,
        summary=summary,
        source_message_text=(note.source or summary).strip(),
    )


def _normalize_note_key(key: str) -> str:
    normalized = _KEY_PATTERN.sub("_", key.casefold()).strip("_")
    if normalized:
        return normalized
    raise ValueError("Preference note key must include at least one letter or number.")
