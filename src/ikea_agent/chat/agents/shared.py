"""Shared helpers for agent-local toolsets and cross-agent context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger
from typing import Protocol, TypeVar

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from ikea_agent.chat.agents.state import CommonAgentState, Room3DSnapshotContext
from ikea_agent.chat.known_fact_context import format_known_fact_context
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.asset_repository import AssetRepository, AssetSnapshot
from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.room_3d_repository import Room3DRepository, Room3DSnapshotEntry
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.types import (
    AttachmentRef,
    AttachmentRefPayload,
    BundleProposalToolResult,
    FloorPlanArtifact,
    FloorPlanRevisionOverview,
    KnownFactMemory,
    Room3DSnapshotArtifact,
    RoomImageAnalysisArtifact,
    RoomImageArtifact,
)
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
AssetRepositoryFactory = Callable[[ChatRuntime], AssetRepository | None]
ContextFactRepositoryFactory = Callable[[ChatRuntime], ContextFactRepository | None]
FloorPlanRepositoryFactory = Callable[[ChatRuntime], FloorPlanRepository | None]
AnalysisRepositoryFactory = Callable[[ChatRuntime], AnalysisRepository | None]
SearchRepositoryFactory = Callable[[ChatRuntime], SearchRepository | None]
Room3DRepositoryFactory = Callable[[ChatRuntime], Room3DRepository | None]

SHARED_CONTEXT_READ_TOOL_NAMES: tuple[str, ...] = (
    "get_project_facts",
    "get_room_facts",
    "list_room_images",
    "get_latest_floor_plan",
    "list_floor_plan_revisions",
    "list_room_image_analyses",
    "list_room_3d_snapshots",
    "list_room_bundle_proposals",
)
SHARED_CONTEXT_WRITE_TOOL_NAMES: tuple[str, ...] = (
    "remember_room_fact",
    "remember_project_fact",
    "rename_room",
    "set_room_type",
)
SHARED_CONTEXT_TOOL_NAMES: tuple[str, ...] = (
    *SHARED_CONTEXT_WRITE_TOOL_NAMES,
    *SHARED_CONTEXT_READ_TOOL_NAMES,
)


@dataclass(frozen=True, slots=True)
class SharedContextToolsetServices:
    """Repository seams used by shared read/write agent tools."""

    get_asset_repository: AssetRepositoryFactory
    get_context_fact_repository: ContextFactRepositoryFactory
    get_floor_plan_repository: FloorPlanRepositoryFactory
    get_analysis_repository: AnalysisRepositoryFactory
    get_search_repository: SearchRepositoryFactory
    get_room_3d_repository: Room3DRepositoryFactory


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


def asset_repository(runtime: ChatRuntime) -> AssetRepository | None:
    """Return asset metadata repository when runtime persistence is available."""

    if not hasattr(runtime, "session_factory"):
        return None
    return AssetRepository(runtime.session_factory)


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


def default_shared_context_toolset_services() -> SharedContextToolsetServices:
    """Return the default persistence seams for shared context tools."""

    return SharedContextToolsetServices(
        get_asset_repository=asset_repository,
        get_context_fact_repository=context_fact_repository,
        get_floor_plan_repository=floor_plan_repository,
        get_analysis_repository=analysis_repository,
        get_search_repository=search_repository,
        get_room_3d_repository=room_3d_repository,
    )


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
            "Before asking the user to restate durable room context, "
            "inspect the shared read tools. "
            "Use `get_room_facts`, `get_project_facts`, `list_room_images`, "
            "`get_latest_floor_plan`, and the other `list_room_*` tools "
            "to reuse known room context."
        ),
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


def _sync_room_context_state(
    state: CommonAgentState,
    *,
    room_id: str,
    repository: ContextFactRepository,
) -> tuple[list[KnownFactMemory], list[KnownFactMemory]]:
    """Reload room/project facts and durable room identity into agent state."""

    room_context = repository.load_room_context(room_id=room_id)
    state.set_room_profile(
        project_id=room_context.room_identity.project_id,
        room_title=room_context.room_identity.title,
        room_type=room_context.room_identity.room_type,
    )
    state.room_facts = list(room_context.room_facts)
    state.project_facts = list(room_context.project_facts)
    return state.room_facts, state.project_facts


def _attachment_ref_from_asset(asset: AssetSnapshot) -> AttachmentRef:
    return AttachmentRef(
        attachment_id=asset.asset_id,
        mime_type=asset.mime_type,
        uri=f"/attachments/{asset.asset_id}",
        width=asset.width,
        height=asset.height,
        file_name=asset.file_name,
    )


def _attachment_payload_from_asset(asset: AssetSnapshot) -> AttachmentRefPayload:
    return AttachmentRefPayload.from_ref(_attachment_ref_from_asset(asset))


def _asset_payload_map(
    *,
    asset_repository: AssetRepository | None,
    room_id: str,
    asset_ids: list[str],
) -> dict[str, AttachmentRefPayload]:
    if asset_repository is None or not asset_ids:
        return {}
    return {
        asset.asset_id: _attachment_payload_from_asset(asset)
        for asset in asset_repository.list_assets_by_ids(room_id=room_id, asset_ids=asset_ids)
    }


def build_get_room_facts_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to reload room-scoped durable facts."""

    def get_room_facts(ctx: RunContext[_DepsWithState]) -> list[KnownFactMemory]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room fact reads are unavailable for this runtime.")

        room_facts, _ = _sync_room_context_state(
            ctx.deps.state,
            room_id=room_id,
            repository=repository,
        )
        logger.info(
            "get_room_facts",
            extra={
                "room_fact_count": len(room_facts),
                **telemetry_context(ctx.deps.state),
            },
        )
        return room_facts

    return Tool(get_room_facts, name="get_room_facts")


def build_get_project_facts_tool(
    *,
    get_repository: ContextFactRepositoryFactory = context_fact_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to reload project-scoped durable facts."""

    def get_project_facts(ctx: RunContext[_DepsWithState]) -> list[KnownFactMemory]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Project fact reads are unavailable for this runtime.")

        _, project_facts = _sync_room_context_state(
            ctx.deps.state,
            room_id=room_id,
            repository=repository,
        )
        logger.info(
            "get_project_facts",
            extra={
                "project_fact_count": len(project_facts),
                **telemetry_context(ctx.deps.state),
            },
        )
        return project_facts

    return Tool(get_project_facts, name="get_project_facts")


def build_list_room_images_tool(
    *,
    get_repository: AssetRepositoryFactory = asset_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to reload room-owned uploaded images."""

    def list_room_images(ctx: RunContext[_DepsWithState]) -> list[RoomImageArtifact]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room image reads are unavailable for this runtime.")

        images = [
            RoomImageArtifact(
                attachment=_attachment_payload_from_asset(asset),
                thread_id=asset.thread_id,
                run_id=asset.run_id,
                created_by_tool=asset.created_by_tool,
                created_at=asset.created_at,
            )
            for asset in repository.list_room_images(room_id=room_id)
        ]
        logger.info(
            "list_room_images",
            extra={
                "image_count": len(images),
                **telemetry_context(ctx.deps.state),
            },
        )
        return images

    return Tool(list_room_images, name="list_room_images")


def build_get_latest_floor_plan_tool(
    *,
    get_floor_plan_repository: FloorPlanRepositoryFactory = floor_plan_repository,
    get_asset_repository: AssetRepositoryFactory = asset_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to read the latest persisted floor plan."""

    def get_latest_floor_plan(ctx: RunContext[_DepsWithState]) -> FloorPlanArtifact | None:
        room_id = require_room_id(ctx.deps.state)
        repository = get_floor_plan_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Floor-plan reads are unavailable for this runtime.")

        snapshot = repository.get_latest_revision(room_id=room_id)
        if snapshot is None:
            return None

        asset_ids = [
            asset_id
            for asset_id in (snapshot.svg_asset_id, snapshot.png_asset_id)
            if asset_id is not None
        ]
        assets_by_id = _asset_payload_map(
            asset_repository=get_asset_repository(ctx.deps.runtime),
            room_id=room_id,
            asset_ids=asset_ids,
        )
        result = FloorPlanArtifact(
            floor_plan_revision_id=snapshot.floor_plan_revision_id,
            room_id=snapshot.room_id,
            thread_id=snapshot.thread_id,
            revision=snapshot.revision,
            scene_level=snapshot.scene_level,
            scene=snapshot.scene.model_dump(mode="json"),
            summary=snapshot.summary,
            svg_attachment=assets_by_id.get(snapshot.svg_asset_id or ""),
            png_attachment=assets_by_id.get(snapshot.png_asset_id or ""),
            confirmed_at=snapshot.confirmed_at,
            confirmed_by_run_id=snapshot.confirmed_by_run_id,
            confirmation_note=snapshot.confirmation_note,
            created_at=snapshot.created_at,
        )
        logger.info(
            "get_latest_floor_plan",
            extra={
                "revision": result.revision,
                **telemetry_context(ctx.deps.state),
            },
        )
        return result

    return Tool(get_latest_floor_plan, name="get_latest_floor_plan")


def build_list_floor_plan_revisions_tool(
    *,
    get_repository: FloorPlanRepositoryFactory = floor_plan_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to list persisted floor-plan revisions."""

    def list_floor_plan_revisions(
        ctx: RunContext[_DepsWithState],
    ) -> list[FloorPlanRevisionOverview]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Floor-plan revision reads are unavailable for this runtime.")

        revisions = [
            FloorPlanRevisionOverview(
                floor_plan_revision_id=snapshot.floor_plan_revision_id,
                revision=snapshot.revision,
                scene_level=snapshot.scene_level,
                summary=snapshot.summary,
                thread_id=snapshot.thread_id,
                confirmed_at=snapshot.confirmed_at,
                confirmation_note=snapshot.confirmation_note,
                created_at=snapshot.created_at,
            )
            for snapshot in repository.list_revisions(room_id=room_id)
        ]
        logger.info(
            "list_floor_plan_revisions",
            extra={
                "revision_count": len(revisions),
                **telemetry_context(ctx.deps.state),
            },
        )
        return revisions

    return Tool(list_floor_plan_revisions, name="list_floor_plan_revisions")


def build_list_room_image_analyses_tool(
    *,
    get_analysis_repository: AnalysisRepositoryFactory = analysis_repository,
    get_asset_repository: AssetRepositoryFactory = asset_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to list room image analyses."""

    def list_room_image_analyses(
        ctx: RunContext[_DepsWithState],
    ) -> list[RoomImageAnalysisArtifact]:
        room_id = require_room_id(ctx.deps.state)
        analysis_repo = get_analysis_repository(ctx.deps.runtime)
        if analysis_repo is None:
            raise ValueError("Image-analysis reads are unavailable for this runtime.")

        snapshots = analysis_repo.list_room_analyses(room_id=room_id)
        asset_ids = [asset_id for snapshot in snapshots for asset_id in snapshot.input_asset_ids]
        assets_by_id = _asset_payload_map(
            asset_repository=get_asset_repository(ctx.deps.runtime),
            room_id=room_id,
            asset_ids=asset_ids,
        )
        analyses = [
            RoomImageAnalysisArtifact(
                analysis_id=snapshot.analysis_id,
                tool_name=snapshot.tool_name,
                thread_id=snapshot.thread_id,
                run_id=snapshot.run_id,
                input_images=[
                    assets_by_id[asset_id]
                    for asset_id in snapshot.input_asset_ids
                    if asset_id in assets_by_id
                ],
                request=snapshot.request,
                result=snapshot.result,
                created_at=snapshot.created_at,
            )
            for snapshot in snapshots
        ]
        logger.info(
            "list_room_image_analyses",
            extra={
                "analysis_count": len(analyses),
                **telemetry_context(ctx.deps.state),
            },
        )
        return analyses

    return Tool(list_room_image_analyses, name="list_room_image_analyses")


def build_list_room_3d_snapshots_tool(
    *,
    get_room_3d_repository: Room3DRepositoryFactory = room_3d_repository,
    get_asset_repository: AssetRepositoryFactory = asset_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to list persisted room 3D snapshots."""

    def list_room_3d_snapshots(
        ctx: RunContext[_DepsWithState],
    ) -> list[Room3DSnapshotArtifact]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_room_3d_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Room 3D snapshot reads are unavailable for this runtime.")

        snapshots = repository.list_room_3d_snapshots(room_id=room_id)
        asset_ids = [snapshot.snapshot_asset_id for snapshot in snapshots]
        assets_by_id = _asset_payload_map(
            asset_repository=get_asset_repository(ctx.deps.runtime),
            room_id=room_id,
            asset_ids=asset_ids,
        )
        result = [
            Room3DSnapshotArtifact(
                room_3d_snapshot_id=snapshot.room_3d_snapshot_id,
                thread_id=snapshot.thread_id,
                run_id=snapshot.run_id,
                snapshot_image=assets_by_id.get(snapshot.snapshot_asset_id),
                room_3d_asset_id=snapshot.room_3d_asset_id,
                camera=snapshot.camera,
                lighting=snapshot.lighting,
                comment=snapshot.comment,
                created_at=snapshot.created_at,
            )
            for snapshot in snapshots
        ]
        logger.info(
            "list_room_3d_snapshots",
            extra={
                "snapshot_count": len(result),
                **telemetry_context(ctx.deps.state),
            },
        )
        return result

    return Tool(list_room_3d_snapshots, name="list_room_3d_snapshots")


def build_list_room_bundle_proposals_tool(
    *,
    get_repository: SearchRepositoryFactory = search_repository,
) -> Tool[_DepsWithState]:
    """Build the shared tool agents use to list room-owned bundle proposals."""

    def list_room_bundle_proposals(
        ctx: RunContext[_DepsWithState],
    ) -> list[BundleProposalToolResult]:
        room_id = require_room_id(ctx.deps.state)
        repository = get_repository(ctx.deps.runtime)
        if repository is None:
            raise ValueError("Bundle proposal reads are unavailable for this runtime.")

        proposals = repository.list_bundle_proposals(room_id=room_id)
        logger.info(
            "list_room_bundle_proposals",
            extra={
                "bundle_count": len(proposals),
                **telemetry_context(ctx.deps.state),
            },
        )
        return proposals

    return Tool(list_room_bundle_proposals, name="list_room_bundle_proposals")


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


def build_shared_context_read_tools(
    services: SharedContextToolsetServices | None = None,
) -> list[Tool[_DepsWithState]]:
    """Return the shared read-only room/project tools used by all first-class agents."""

    resolved_services = services or default_shared_context_toolset_services()

    return [
        build_get_project_facts_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
        build_get_room_facts_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
        build_list_room_images_tool(
            get_repository=resolved_services.get_asset_repository,
        ),
        build_get_latest_floor_plan_tool(
            get_floor_plan_repository=resolved_services.get_floor_plan_repository,
            get_asset_repository=resolved_services.get_asset_repository,
        ),
        build_list_floor_plan_revisions_tool(
            get_repository=resolved_services.get_floor_plan_repository,
        ),
        build_list_room_image_analyses_tool(
            get_analysis_repository=resolved_services.get_analysis_repository,
            get_asset_repository=resolved_services.get_asset_repository,
        ),
        build_list_room_3d_snapshots_tool(
            get_room_3d_repository=resolved_services.get_room_3d_repository,
            get_asset_repository=resolved_services.get_asset_repository,
        ),
        build_list_room_bundle_proposals_tool(
            get_repository=resolved_services.get_search_repository,
        ),
    ]


def build_shared_context_write_tools(
    services: SharedContextToolsetServices | None = None,
) -> list[Tool[_DepsWithState]]:
    """Return the shared durable write tools used by all first-class agents."""

    resolved_services = services or default_shared_context_toolset_services()

    return [
        build_remember_room_fact_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
        build_remember_project_fact_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
        build_rename_room_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
        build_set_room_type_tool(
            get_repository=resolved_services.get_context_fact_repository,
        ),
    ]


def build_shared_context_tools(
    services: SharedContextToolsetServices | None = None,
) -> list[Tool[_DepsWithState]]:
    """Return the shared durable-context tools used by all first-class agents."""

    return [
        *build_shared_context_write_tools(services),
        *build_shared_context_read_tools(services),
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
