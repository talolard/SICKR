"""Shared AG-UI state models for agent-first runtime."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ikea_agent.shared.types import AttachmentRef


class Room3DSnapshotCamera(BaseModel):
    """Camera metadata captured with one 3D perspective snapshot."""

    position_m: tuple[float, float, float]
    target_m: tuple[float, float, float]
    fov_deg: float


class Room3DSnapshotLighting(BaseModel):
    """Lighting emphasis metadata captured with one 3D snapshot."""

    light_fixture_ids: list[str] = Field(default_factory=list)
    emphasized_light_count: int = 0


class Room3DSnapshotContext(BaseModel):
    """UI-originated 3D snapshot context item shared into agent state."""

    snapshot_id: str
    attachment: AttachmentRef
    comment: str | None = None
    captured_at: str
    camera: Room3DSnapshotCamera
    lighting: Room3DSnapshotLighting


class CommonAgentState(BaseModel):
    """Common AG-UI state fields used by all first-class agents."""

    session_id: str | None = None
    branch_from_session_id: str | None = None
    thread_id: str | None = None
    run_id: str | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)


class FloorPlanIntakeAgentState(CommonAgentState):
    """State for floor-plan intake agent runs."""


class SearchAgentState(CommonAgentState):
    """State for search agent runs."""

    room_3d_snapshots: list[Room3DSnapshotContext] = Field(default_factory=list)


class ImageAnalysisAgentState(CommonAgentState):
    """State for image-analysis agent runs."""
