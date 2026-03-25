"""Typed FastAPI response models for room/thread persistence APIs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ikea_agent.shared.types import KnownFactKind, KnownFactScope, RoomType


class ThreadDetailItem(BaseModel):
    """Thread detail including aggregate child counts."""

    thread_id: str
    title: str | None
    room_id: str
    room_title: str
    room_type: RoomType | None
    status: str
    last_activity_at: str | None
    run_count: int
    asset_count: int
    floor_plan_revision_count: int
    analysis_count: int
    search_count: int


class ThreadListItem(BaseModel):
    """Lightweight thread metadata for room-scoped thread pickers."""

    thread_id: str
    room_id: str
    title: str | None
    status: str
    last_activity_at: str | None


class AssetListItem(BaseModel):
    """One stored asset entry for thread inspection UIs."""

    asset_id: str
    uri: str
    run_id: str | None
    created_by_tool: str | None
    kind: str
    display_label: str | None = None
    mime_type: str
    file_name: str | None
    size_bytes: int
    created_at: str | None


class KnownFactItem(BaseModel):
    """One durable room- or project-scoped fact for UI display."""

    fact_id: str
    scope: KnownFactScope
    kind: KnownFactKind
    summary: str
    source_message_text: str
    updated_at: str
    run_id: str | None


class AnalysisFeedbackCreateRequest(BaseModel):
    """Request payload to persist one user feedback decision on an analysis."""

    feedback_kind: Literal["confirm", "reject", "uncertain"]
    mask_ordinal: int | None = Field(default=None, ge=1)
    mask_label: str | None = None
    query_text: str | None = None
    note: str | None = None
    run_id: str | None = None


class ThreadCreateRequest(BaseModel):
    """Request payload to create one explicit thread row for a room."""

    title: str | None = None


class AnalysisFeedbackItem(BaseModel):
    """One persisted user feedback decision for an analysis entry."""

    analysis_feedback_id: str
    analysis_id: str
    thread_id: str
    run_id: str | None
    feedback_kind: Literal["confirm", "reject", "uncertain"]
    mask_ordinal: int | None
    mask_label: str | None
    query_text: str | None
    note: str | None
    created_at: str


class ThreadTranscriptResponse(BaseModel):
    """Canonical transcript payload for one room/thread pair."""

    room_id: str
    thread_id: str
    messages: list[dict[str, object]]
