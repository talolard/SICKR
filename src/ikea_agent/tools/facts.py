"""Shared models and helpers for durable fact capture and room identity tools."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from ikea_agent.shared.types import (
    KnownFactKind,
    KnownFactMemory,
    KnownFactMemoryInput,
    RoomIdentity,
    RoomType,
)

_KEY_PATTERN = re.compile(r"[^a-z0-9]+")


class FactNoteInput(BaseModel):
    """Compact durable fact note authored by an agent."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    kind: KnownFactKind
    summary: str = Field(min_length=1)
    source: str | None = None


class FactNoteResult(BaseModel):
    """Result returned after storing one durable room or project fact."""

    model_config = ConfigDict(extra="forbid")

    message: str
    fact: KnownFactMemory


class RenameRoomInput(BaseModel):
    """Durable room-title update authored by an agent."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=512)


class RenameRoomResult(BaseModel):
    """Result returned after updating the room title."""

    model_config = ConfigDict(extra="forbid")

    message: str
    room: RoomIdentity


class SetRoomTypeInput(BaseModel):
    """Durable room-type update authored by an agent."""

    model_config = ConfigDict(extra="forbid")

    room_type: RoomType


class SetRoomTypeResult(BaseModel):
    """Result returned after updating the room type."""

    model_config = ConfigDict(extra="forbid")

    message: str
    room: RoomIdentity


def note_to_known_fact_input(note: FactNoteInput) -> KnownFactMemoryInput:
    """Normalize one explicit note into the persisted known-fact input shape."""

    normalized_key = _normalize_note_key(note.key)
    summary = note.summary.strip()
    return KnownFactMemoryInput(
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
    raise ValueError("Fact note key must include at least one letter or number.")
