"""Shared helpers for agent-local toolsets and cross-agent context."""

from __future__ import annotations

from collections.abc import Callable
from logging import getLogger
from typing import Protocol, TypeVar

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from ikea_agent.chat.agents.state import CommonAgentState, Room3DSnapshotContext
from ikea_agent.chat.revealed_preference_memory import format_preference_context
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.revealed_preference_repository import (
    RevealedPreferenceRepository,
)
from ikea_agent.persistence.room_3d_repository import Room3DRepository, Room3DSnapshotEntry
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.tools.preferences import (
    PreferenceNoteInput,
    PreferenceNoteResult,
    note_to_memory_input,
)

logger = getLogger(__name__)


class _HasState(Protocol):
    state: CommonAgentState
    runtime: ChatRuntime


_DepsWithState = TypeVar("_DepsWithState", bound=_HasState)
PreferenceRepositoryFactory = Callable[[ChatRuntime], RevealedPreferenceRepository | None]


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


def revealed_preference_repository(runtime: ChatRuntime) -> RevealedPreferenceRepository | None:
    """Return revealed-preference repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return RevealedPreferenceRepository(runtime.session_factory)


def _preference_instruction_text(state: CommonAgentState) -> str:
    """Render the shared durable-preference policy plus current thread context."""

    context_block = format_preference_context(state.revealed_preferences)
    lines = [
        (
            "When the user reveals a durable fact, constraint, or taste that "
            "should matter in later turns, call `remember_preference` with a "
            "short summary."
        ),
        (
            "Use that tool for compact notes such as `user_has_toddlers` with "
            "summary `User has toddlers, keep things elevated.`"
        ),
    ]
    if context_block is not None:
        lines.append(context_block)
    return "\n".join(lines)


def build_preference_instruction[DepsT: _HasState]() -> Callable[[RunContext[DepsT]], str]:
    """Build one typed instruction callback for agent-specific deps."""

    def preference_instruction(ctx: RunContext[DepsT]) -> str:
        return _preference_instruction_text(ctx.deps.state)

    return preference_instruction


def build_remember_preference_tool(
    *,
    get_repository: PreferenceRepositoryFactory = revealed_preference_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to persist durable thread preferences."""

    def remember_preference(
        ctx: RunContext[_DepsWithState],
        note: PreferenceNoteInput,
    ) -> PreferenceNoteResult:
        thread_id = ctx.deps.state.thread_id
        if thread_id is None:
            raise ValueError("Thread preference memory requires a thread_id in agent state.")
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Thread preference memory is unavailable for this runtime.")

        memory_input = note_to_memory_input(note)
        persisted = repository.upsert_preferences(
            thread_id=thread_id,
            run_id=ctx.deps.state.run_id,
            preferences=[memory_input],
        )
        stored = next(
            item
            for item in persisted
            if item.signal_key == memory_input.signal_key and item.value == memory_input.value
        )
        ctx.deps.state.remember_preference(stored)
        logger.info(
            "remember_preference",
            extra={
                "thread_id": thread_id,
                "run_id": ctx.deps.state.run_id,
                "kind": note.kind,
                "key": stored.value,
                **telemetry_context(ctx.deps.state),
            },
        )
        return PreferenceNoteResult(
            message="Stored durable thread preference note.",
            memory=stored,
        )

    return Tool(remember_preference, name="remember_preference")


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
