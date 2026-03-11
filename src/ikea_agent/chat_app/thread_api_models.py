"""Typed FastAPI response models for thread-scoped persistence APIs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class Room3DAssetCreateRequest(BaseModel):
    """Create request for one room 3D asset binding."""

    source_asset_id: str
    usd_format: str
    metadata: dict[str, object]
    run_id: str | None = None


class Room3DAssetListItem(BaseModel):
    """One persisted room 3D asset row for thread APIs."""

    room_3d_asset_id: str
    thread_id: str
    run_id: str | None
    source_asset_id: str
    usd_format: str
    metadata: dict[str, object]
    created_at: str


class Room3DSnapshotCreateRequest(BaseModel):
    """Create request for one room 3D snapshot metadata row."""

    snapshot_asset_id: str
    room_3d_asset_id: str | None = None
    camera: dict[str, object]
    lighting: dict[str, object]
    comment: str | None = None
    run_id: str | None = None


class Room3DSnapshotListItem(BaseModel):
    """One persisted room 3D snapshot row for thread APIs."""

    room_3d_snapshot_id: str
    thread_id: str
    run_id: str | None
    snapshot_asset_id: str
    room_3d_asset_id: str | None
    camera: dict[str, object]
    lighting: dict[str, object]
    comment: str | None
    created_at: str


class CommentBundleCreateResponse(BaseModel):
    """Response payload for one persisted UI feedback bundle."""

    comment_id: str
    directory: str
    markdown_path: str
    saved_images_count: int


class CommentBundleCreateRequest(BaseModel):
    """Request payload for persisting one UI feedback bundle."""

    title: str | None = None
    comment: str = ""
    page_url: str | None = None
    thread_id: str | None = None
    user_agent: str | None = None
    include_console_log: bool = True
    include_dom_snapshot: bool = True
    include_ui_state: bool = True
    console_log: str | None = None
    dom_snapshot: str | None = None
    ui_state: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
