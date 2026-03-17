"""Typed FastAPI response models for thread-scoped persistence APIs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ThreadDetailItem(BaseModel):
    """Thread detail including aggregate child counts."""

    thread_id: str
    title: str | None
    status: str
    last_activity_at: str | None
    run_count: int
    asset_count: int
    floor_plan_revision_count: int
    analysis_count: int
    search_count: int


class AssetListItem(BaseModel):
    """One stored asset entry for thread inspection UIs."""

    asset_id: str
    run_id: str | None
    created_by_tool: str | None
    kind: str
    mime_type: str
    file_name: str | None
    storage_path: str
    size_bytes: int
    created_at: str | None


class AnalysisFeedbackCreateRequest(BaseModel):
    """Request payload to persist one user feedback decision on an analysis."""

    feedback_kind: Literal["confirm", "reject", "uncertain"]
    mask_ordinal: int | None = Field(default=None, ge=1)
    mask_label: str | None = None
    query_text: str | None = None
    note: str | None = None
    run_id: str | None = None


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


class TraceReportCreateRequest(BaseModel):
    """Request payload for persisting one current-thread trace report."""

    title: str = Field(min_length=1)
    description: str | None = None
    thread_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    page_url: str | None = None
    user_agent: str | None = None
    include_console_log: bool = True
    console_log: str | None = None


class RecentTraceReportItem(BaseModel):
    """Small summary payload for recent saved trace bundles."""

    trace_id: str
    title: str
    created_at: str
    thread_id: str | None = None
    agent_name: str | None = None
    directory: str
    markdown_path: str


class RecentTraceReportListResponse(BaseModel):
    """Response payload for recent saved trace bundles."""

    traces: list[RecentTraceReportItem] = Field(default_factory=list)


class TraceReportCreateResponse(BaseModel):
    """Response payload for one saved trace report bundle."""

    trace_id: str
    directory: str
    trace_json_path: str
    markdown_path: str
    beads_epic_id: str | None = None
    beads_task_id: str | None = None
    status: Literal["saved_and_linked", "saved_without_beads"]
