"""Shared helpers for agent-local toolsets."""

from __future__ import annotations

from ikea_agent.chat.agents.state import CommonAgentState, Room3DSnapshotContext
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.room_3d_repository import Room3DRepository, Room3DSnapshotEntry
from ikea_agent.persistence.search_repository import SearchRepository


def telemetry_context(state: CommonAgentState) -> dict[str, str | None]:
    """Return stable trace context fields for agent-tool logs."""

    return {
        "session_id": state.session_id,
        "branch_from_session_id": state.branch_from_session_id,
    }


def floor_plan_repository(runtime: ChatRuntime) -> FloorPlanRepository | None:
    """Return floor-plan persistence repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return FloorPlanRepository(runtime.session_factory)


def analysis_repository(runtime: ChatRuntime) -> AnalysisRepository | None:
    """Return image-analysis repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return AnalysisRepository(runtime.session_factory)


def search_repository(runtime: ChatRuntime) -> SearchRepository | None:
    """Return search repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return SearchRepository(runtime.session_factory)


def room_3d_repository(runtime: ChatRuntime) -> Room3DRepository | None:
    """Return 3D room snapshot repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return Room3DRepository(runtime.session_factory)


def build_room_3d_snapshot_context_payload(
    *,
    state_snapshots: list[Room3DSnapshotContext],
    persisted_snapshots: list[Room3DSnapshotEntry],
) -> dict[str, object]:
    """Build one stable payload that merges UI and persisted 3D snapshot context."""

    persisted_payload = [
        {
            "room_3d_snapshot_id": snapshot.room_3d_snapshot_id,
            "snapshot_asset_id": snapshot.snapshot_asset_id,
            "room_3d_asset_id": snapshot.room_3d_asset_id,
            "camera": snapshot.camera,
            "lighting": snapshot.lighting,
            "comment": snapshot.comment,
            "created_at": snapshot.created_at,
        }
        for snapshot in persisted_snapshots
    ]
    return {
        "state_snapshots": [snapshot.model_dump(mode="json") for snapshot in state_snapshots],
        "persisted_snapshots": persisted_payload,
        "state_count": len(state_snapshots),
        "persisted_count": len(persisted_payload),
    }
