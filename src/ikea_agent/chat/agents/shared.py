"""Shared helpers for agent-local toolsets and cross-agent context."""

from __future__ import annotations

from collections.abc import Callable
from logging import getLogger
from typing import Protocol, TypeVar

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from ikea_agent.chat.agents.state import CommonAgentState, Room3DSnapshotContext
from ikea_agent.chat.known_fact_context import format_known_fact_context
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.room_3d_repository import Room3DRepository, Room3DSnapshotEntry
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.tools.facts import (
    FactNoteInput,
    FactNoteResult,
    RenameRoomInput,
    RenameRoomResult,
    SetRoomTypeInput,
    SetRoomTypeResult,
    note_to_known_fact_input,
)

logger = getLogger(__name__)


class _HasState(Protocol):
    state: CommonAgentState
    runtime: ChatRuntime


_DepsWithState = TypeVar("_DepsWithState", bound=_HasState)
ContextFactRepositoryFactory = Callable[[ChatRuntime], ContextFactRepository | None]


def telemetry_context(state: CommonAgentState) -> dict[str, str | None]:
    """Return stable trace context fields for agent-tool logs."""

    return {
        "session_id": state.session_id,
        "branch_from_session_id": state.branch_from_session_id,
        "project_id": state.project_id,
        "room_id": state.room_id,
        "thread_id": state.thread_id,
    }


def require_thread_id(state: CommonAgentState) -> str:
    """Return the active thread id or fail when durable thread context is missing."""

    thread_id = state.thread_id
    if thread_id is None:
        raise ValueError("Agent state requires an explicit thread_id for durable writes.")
    return thread_id


def require_room_id(state: CommonAgentState) -> str:
    """Return the active room id or fail when durable room context is missing."""

    room_id = state.room_id
    if room_id is None:
        raise ValueError("Agent state requires an explicit room_id for durable writes.")
    return room_id


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


def context_fact_repository(runtime: ChatRuntime) -> ContextFactRepository | None:
    """Return durable room/project fact repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return ContextFactRepository(runtime.session_factory)


def _fact_instruction_text(state: CommonAgentState) -> str:
    """Render the shared durable-fact policy plus current room/project context."""

    context_block = format_known_fact_context(
        room_title=state.room_title,
        room_type=state.room_type,
        room_facts=state.room_facts,
        project_facts=state.project_facts,
    )
    lines = [
        (
            "When the user reveals a durable fact, constraint, or taste that should matter later, "
            "store it explicitly. Use `remember_room_fact` for room-specific context and "
            "`remember_project_fact` for project-wide context."
        ),
        (
            "If the user directly identifies the room name or room type and the current room "
            "identity is missing or inaccurate, call `rename_room` or `set_room_type`."
        ),
        (
            "Bias toward setting room title/type early when they are unknown. Once they are set, "
            "avoid changing them unless the user clearly corrects or reframes the room."
        ),
        (
            "Do not store the current shopping request itself as a durable fact. Looking for a "
            "couch, table, or lamp is part of the current request unless the user clearly states "
            "it as enduring context."
        ),
    ]
    if context_block is not None:
        lines.extend(["", context_block])
    return "\n".join(lines)


def build_known_fact_instruction[DepsT: _HasState]() -> Callable[[RunContext[DepsT]], str]:
    """Build one typed instruction callback for room/project fact context."""

    def known_fact_instruction(ctx: RunContext[DepsT]) -> str:
        return _fact_instruction_text(ctx.deps.state)

    return known_fact_instruction


def build_remember_room_fact_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to persist room-scoped durable facts."""

    def remember_room_fact(
        ctx: RunContext[_DepsWithState],
        note: FactNoteInput,
    ) -> FactNoteResult:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room fact memory is unavailable for this runtime.")

        fact_input = note_to_known_fact_input(note)
        persisted = repository.upsert_room_facts(
            room_id=room_id,
            run_id=ctx.deps.state.run_id,
            facts=[fact_input],
        )
        stored = next(
            item
            for item in persisted
            if item.signal_key == fact_input.signal_key and item.value == fact_input.value
        )
        ctx.deps.state.remember_room_fact(stored)
        logger.info(
            "remember_room_fact",
            extra={
                "run_id": ctx.deps.state.run_id,
                "kind": note.kind,
                "key": stored.value,
                **telemetry_context(ctx.deps.state),
            },
        )
        return FactNoteResult(
            message="Stored durable room fact.",
            fact=stored,
        )

    return Tool(remember_room_fact, name="remember_room_fact")


def build_remember_project_fact_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to persist project-scoped durable facts."""

    def remember_project_fact(
        ctx: RunContext[_DepsWithState],
        note: FactNoteInput,
    ) -> FactNoteResult:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Project fact memory is unavailable for this runtime.")

        room_context = repository.load_room_context(room_id=room_id)
        ctx.deps.state.set_room_profile(
            project_id=room_context.room_identity.project_id,
            room_title=room_context.room_identity.title,
            room_type=room_context.room_identity.room_type,
        )
        fact_input = note_to_known_fact_input(note)
        persisted = repository.upsert_project_facts(
            project_id=room_context.room_identity.project_id,
            run_id=ctx.deps.state.run_id,
            facts=[fact_input],
        )
        stored = next(
            item
            for item in persisted
            if item.signal_key == fact_input.signal_key and item.value == fact_input.value
        )
        ctx.deps.state.remember_project_fact(stored)
        logger.info(
            "remember_project_fact",
            extra={
                "run_id": ctx.deps.state.run_id,
                "kind": note.kind,
                "key": stored.value,
                **telemetry_context(ctx.deps.state),
            },
        )
        return FactNoteResult(
            message="Stored durable project fact.",
            fact=stored,
        )

    return Tool(remember_project_fact, name="remember_project_fact")


def build_rename_room_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to persist room titles."""

    def rename_room(
        ctx: RunContext[_DepsWithState],
        update_request: RenameRoomInput,
    ) -> RenameRoomResult:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room rename writes are unavailable for this runtime.")

        room_identity = repository.rename_room(room_id=room_id, title=update_request.title)
        ctx.deps.state.set_room_profile(
            project_id=room_identity.project_id,
            room_title=room_identity.title,
            room_type=room_identity.room_type,
        )
        logger.info(
            "rename_room",
            extra=telemetry_context(ctx.deps.state),
        )
        return RenameRoomResult(
            message="Updated durable room title.",
            room=room_identity,
        )

    return Tool(rename_room, name="rename_room")


def build_set_room_type_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to persist room types."""

    def set_room_type(
        ctx: RunContext[_DepsWithState],
        update_request: SetRoomTypeInput,
    ) -> SetRoomTypeResult:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room-type writes are unavailable for this runtime.")

        room_identity = repository.set_room_type(
            room_id=room_id,
            room_type=update_request.room_type,
        )
        ctx.deps.state.set_room_profile(
            project_id=room_identity.project_id,
            room_title=room_identity.title,
            room_type=room_identity.room_type,
        )
        logger.info(
            "set_room_type",
            extra=telemetry_context(ctx.deps.state),
        )
        return SetRoomTypeResult(
            message="Updated durable room type.",
            room=room_identity,
        )

    return Tool(set_room_type, name="set_room_type")


def build_shared_context_tools() -> list[Tool[_DepsWithState]]:
    """Return the shared durable-context tools used by all first-class agents."""

    return [
        build_remember_room_fact_tool(),
        build_remember_project_fact_tool(),
        build_rename_room_tool(),
        build_set_room_type_tool(),
    ]


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
