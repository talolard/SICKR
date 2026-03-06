"""Typed FastAPI response models for thread-scoped persistence APIs."""

from __future__ import annotations

from pydantic import BaseModel


class ThreadListItem(BaseModel):
    """Lightweight thread summary for thread list UIs."""

    thread_id: str
    title: str | None
    status: str
    last_activity_at: str | None


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


class ThreadTitleUpdateRequest(BaseModel):
    """Request payload to set a user-visible thread title."""

    title: str | None


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


class FloorPlanRevisionListItem(BaseModel):
    """One persisted floor-plan revision entry for a thread."""

    floor_plan_revision_id: str
    revision: int
    scene_level: str
    svg_asset_id: str | None
    png_asset_id: str | None
    confirmed_at: str | None
    confirmed_by_run_id: str | None
    confirmation_note: str | None
    summary: dict[str, object]
    created_at: str | None


class AnalysisListItem(BaseModel):
    """One persisted image-analysis run for a thread."""

    analysis_id: str
    run_id: str | None
    tool_name: str
    input_asset_id: str
    created_at: str | None


class DetectionListItem(BaseModel):
    """Normalized detection row associated with one input image."""

    analysis_detection_id: str
    analysis_id: str
    ordinal: int
    label: str
    bbox_x1_px: int
    bbox_y1_px: int
    bbox_x2_px: int
    bbox_y2_px: int
    bbox_x1_norm: float
    bbox_y1_norm: float
    bbox_x2_norm: float
    bbox_y2_norm: float
