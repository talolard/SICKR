"""Typed dependency container and shared AG-UI state for the chat agent."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import AttachmentRef
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore


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


class ChatAgentState(BaseModel):
    """State shared between CopilotKit UI and PydanticAI agent runs."""

    session_id: str | None = None
    branch_from_session_id: str | None = None
    labels: list[str] = Field(default_factory=list)
    eval_dataset_name: str | None = None
    eval_case_id: str | None = None
    thread_id: str | None = None
    run_id: str | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)
    room_3d_snapshots: list[Room3DSnapshotContext] = Field(default_factory=list)
    subagent_state: dict[str, dict[str, dict[str, object]]] = Field(default_factory=dict)
    subagent_turn_history: dict[str, dict[str, list[dict[str, object]]]] = Field(
        default_factory=dict
    )


@dataclass(slots=True)
class ChatAgentDeps:
    """Agent deps that satisfy AG-UI StateHandler via a `state` field."""

    runtime: ChatRuntime
    attachment_store: AttachmentStore
    floor_plan_scene_store: FloorPlanSceneStore
    state: ChatAgentState
