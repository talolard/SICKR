from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import Tool
from pydantic_ai.usage import RunUsage
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import build_search_toolset
from ikea_agent.chat.agents.shared import (
    build_known_fact_instruction,
    build_shared_context_tools,
)
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore, StoredAttachment
from ikea_agent.chat_app.main import create_app
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.floor_plan_repository import FloorPlanRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.ownership import (
    DEFAULT_DEV_PROJECT_ID,
    DEFAULT_DEV_ROOM_ID,
    ensure_default_dev_hierarchy_for_session_factory,
)
from ikea_agent.persistence.room_3d_repository import Room3DRepository
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.sqlalchemy_db import create_session_factory
from ikea_agent.shared.types import (
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
)
from ikea_agent.tools.facts import (
    FactNoteInput,
    RenameRoomInput,
    SetRoomTypeInput,
    note_to_known_fact_input,
)
from ikea_agent.tools.floorplanner.models import BaselineFloorPlanScene, scene_to_summary

KNOWN_FACT_INSTRUCTION: Callable[[RunContext[SearchAgentDeps]], str] = cast(
    "Callable[[RunContext[SearchAgentDeps]], str]", build_known_fact_instruction()
)


@dataclass(frozen=True, slots=True)
class _PersistenceRuntime:
    sqlalchemy_engine: Engine
    session_factory: sessionmaker[Session]


@dataclass(frozen=True, slots=True)
class _SharedReadArtifacts:
    first_image: StoredAttachment
    second_image: StoredAttachment
    floor_plan_png: StoredAttachment
    floor_plan_svg: StoredAttachment
    snapshot_image: StoredAttachment
    room_3d_asset_id: str


@pytest.fixture(autouse=True)
def _set_fake_google_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-api-key")


def _runtime(tmp_path: Path) -> _PersistenceRuntime:
    engine = create_sqlite_engine(tmp_path / "known_fact_api_test.sqlite")
    ensure_persistence_schema(engine)
    session_factory = create_session_factory(engine)
    ensure_default_dev_hierarchy_for_session_factory(session_factory)
    return _PersistenceRuntime(
        sqlalchemy_engine=engine,
        session_factory=session_factory,
    )


def _payload(*, thread_id: str, run_id: str, text: str) -> dict[str, object]:
    return {
        "roomId": DEFAULT_DEV_ROOM_ID,
        "threadId": thread_id,
        "runId": run_id,
        "state": {
            "room_id": DEFAULT_DEV_ROOM_ID,
            "session_id": "session-test",
        },
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [
            {
                "id": f"msg-{run_id}",
                "role": "user",
                "content": text,
            }
        ],
    }


def _build_capturing_search_agent(captured_prompts: list[str]) -> Agent[SearchAgentDeps, str]:
    async def _function(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[])

    async def _stream(
        messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> AsyncIterator[str]:
        captured_prompts.append(_flatten_message_text(messages))
        yield "context-aware-response"

    return Agent(
        model=FunctionModel(
            function=_function,
            stream_function=_stream,
            model_name="known-fact-test-agent",
        ),
        deps_type=SearchAgentDeps,
        output_type=str,
        instructions=["Base search instructions.", KNOWN_FACT_INSTRUCTION],
        toolsets=[build_search_toolset()],
        name="agent_search_test",
    )


def _flatten_message_text(messages: list[ModelMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        instructions = getattr(message, "instructions", None)
        if isinstance(instructions, str):
            parts.append(instructions)
        elif isinstance(instructions, list):
            parts.extend(item for item in instructions if isinstance(item, str))
        for part in getattr(message, "parts", []):
            content = getattr(part, "content", None)
            if isinstance(content, str):
                parts.append(content)
    return "\n".join(parts)


def _tool_by_name(name: str) -> Tool[SearchAgentDeps]:
    return next(tool for tool in build_shared_context_tools() if tool.name == name)


def _floor_plan_scene() -> BaselineFloorPlanScene:
    return BaselineFloorPlanScene.model_validate(
        {
            "scene_level": "baseline",
            "architecture": {
                "dimensions_cm": {
                    "length_x_cm": 420.0,
                    "depth_y_cm": 300.0,
                    "height_z_cm": 260.0,
                },
                "walls": [
                    {
                        "wall_id": "w1",
                        "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": 420.0, "y_cm": 0.0},
                    },
                    {
                        "wall_id": "w2",
                        "start_cm": {"x_cm": 420.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": 420.0, "y_cm": 300.0},
                    },
                    {
                        "wall_id": "w3",
                        "start_cm": {"x_cm": 420.0, "y_cm": 300.0},
                        "end_cm": {"x_cm": 0.0, "y_cm": 300.0},
                    },
                ],
            },
            "placements": [
                {
                    "placement_id": "wardrobe",
                    "name": "Wardrobe",
                    "position_cm": {"x_cm": 20.0, "y_cm": 25.0},
                    "size_cm": {"x_cm": 100.0, "y_cm": 60.0, "z_cm": 200.0},
                }
            ],
        }
    )


def _seed_shared_room_context(repository: ContextFactRepository) -> None:
    room_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)
    repository.rename_room(room_id=DEFAULT_DEV_ROOM_ID, title="Son's room")
    repository.set_room_type(room_id=DEFAULT_DEV_ROOM_ID, room_type="bedroom")
    repository.upsert_room_facts(
        room_id=DEFAULT_DEV_ROOM_ID,
        run_id=None,
        facts=[
            note_to_known_fact_input(
                FactNoteInput(
                    key="avoid_low_tables",
                    kind="constraint",
                    summary="Avoid low tables because the user has toddlers.",
                    source="Low tables feel risky around the toddlers.",
                )
            )
        ],
    )
    repository.upsert_project_facts(
        project_id=room_context.room_identity.project_id,
        run_id=None,
        facts=[
            note_to_known_fact_input(
                FactNoteInput(
                    key="avoid_drilling",
                    kind="constraint",
                    summary="Avoid drilling across the project.",
                    source="The rental does not allow drilling.",
                )
            )
        ],
    )


def _seed_shared_read_artifacts(
    *,
    attachment_store: AttachmentStore,
    analysis_repository: AnalysisRepository,
    floor_plan_repository: FloorPlanRepository,
    room_3d_repository: Room3DRepository,
    search_repository: SearchRepository,
) -> _SharedReadArtifacts:
    with attachment_store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-source",
        run_id=None,
    ):
        first_image = attachment_store.save_image_bytes(
            content=b"room-image-1",
            mime_type="image/png",
            filename="room-1.png",
            kind="user_upload",
        )
        floor_plan_png = attachment_store.save_image_bytes(
            content=b"floor-plan-png",
            mime_type="image/png",
            filename="floor-plan.png",
            created_by_tool="render_floor_plan",
            kind="floor_plan_png",
        )
        floor_plan_svg = attachment_store.save_image_bytes(
            content=b"floor-plan-svg",
            mime_type="image/svg+xml",
            filename="floor-plan.svg",
            created_by_tool="render_floor_plan",
            kind="floor_plan_svg",
        )

    with attachment_store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-followup",
        run_id=None,
    ):
        second_image = attachment_store.save_image_bytes(
            content=b"room-image-2",
            mime_type="image/jpeg",
            filename="room-2.jpg",
            kind="user_upload",
        )
        snapshot_image = attachment_store.save_image_bytes(
            content=b"snapshot-image",
            mime_type="image/png",
            filename="snapshot.png",
            created_by_tool="capture_room_3d_snapshot",
            kind="room_3d_snapshot",
        )

    scene = _floor_plan_scene()
    floor_plan_repository.save_revision(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-floor-plan",
        scene=scene,
        summary=scene_to_summary(scene),
        svg_asset_id=floor_plan_svg.ref.attachment_id,
        png_asset_id=floor_plan_png.ref.attachment_id,
    )
    analysis_repository.record_analysis(
        tool_name="get_room_detail_details_from_photo",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-followup",
        run_id=None,
        input_asset_id=first_image.ref.attachment_id,
        input_asset_ids=[first_image.ref.attachment_id, second_image.ref.attachment_id],
        request_json={"images": [first_image.ref.attachment_id, second_image.ref.attachment_id]},
        result_json={"room_type": "bedroom"},
        detections=[],
    )
    room_3d_asset = room_3d_repository.create_room_3d_asset(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-followup",
        source_asset_id=first_image.ref.attachment_id,
        usd_format="usdz",
        metadata={"kind": "scan"},
        run_id=None,
    )
    room_3d_repository.create_room_3d_snapshot(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-followup",
        snapshot_asset_id=snapshot_image.ref.attachment_id,
        camera={
            "position_m": [0.0, 1.5, 2.0],
            "target_m": [0.0, 1.0, 0.0],
            "fov_deg": 65.0,
        },
        lighting={"light_fixture_ids": ["ceiling-main"], "emphasized_light_count": 1},
        comment="Window wall is too dark.",
        room_3d_asset_id=room_3d_asset.room_3d_asset_id,
        run_id=None,
    )
    search_repository.record_bundle_proposal(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-followup",
        run_id=None,
        proposal=BundleProposalToolResult(
            bundle_id="bundle-1",
            title="Kid room starter bundle",
            notes="Room-wide bundle context.",
            budget_cap_eur=500.0,
            items=[
                BundleProposalLineItem(
                    item_id="chair-1",
                    product_name="Chair One",
                    product_url="https://www.ikea.com/de/de/p/chair-one-12345678/",
                    description_text="Desk chair",
                    price_eur=79.99,
                    quantity=1,
                    line_total_eur=79.99,
                    reason="Primary seating",
                )
            ],
            bundle_total_eur=79.99,
            validations=[
                BundleValidationResult(
                    kind="pricing_complete",
                    status="pass",
                    message="All bundle items have prices.",
                )
            ],
            created_at="2026-03-11T10:00:00+00:00",
            run_id=None,
        ),
    )
    return _SharedReadArtifacts(
        first_image=first_image,
        second_image=second_image,
        floor_plan_png=floor_plan_png,
        floor_plan_svg=floor_plan_svg,
        snapshot_image=snapshot_image,
        room_3d_asset_id=room_3d_asset.room_3d_asset_id,
    )


def test_flatten_message_text_handles_instruction_lists_and_non_text_parts() -> None:
    message = SimpleNamespace(
        instructions=["first", 2, "second"],
        parts=[
            SimpleNamespace(content="body"),
            SimpleNamespace(content=3),
        ],
    )

    flattened = _flatten_message_text(cast("list[ModelMessage]", [message]))

    assert flattened == "first\nsecond\nbody"


def test_shared_context_tools_persist_facts_and_room_identity(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    repository = ContextFactRepository(runtime.session_factory)
    attachment_store = AttachmentStore(tmp_path / "attachments")
    deps = SearchAgentDeps(
        runtime=cast("ChatRuntime", runtime),
        attachment_store=attachment_store,
        state=SearchAgentState(
            project_id=DEFAULT_DEV_PROJECT_ID,
            room_id=DEFAULT_DEV_ROOM_ID,
            thread_id="thread-pref",
            run_id="run-1",
        ),
    )
    ctx = RunContext[SearchAgentDeps](
        deps=deps,
        model=TestModel(),
        usage=RunUsage(),
        prompt="remember room fact",
        tool_name="remember_room_fact",
    )

    room_fact_tool = _tool_by_name("remember_room_fact")
    project_fact_tool = _tool_by_name("remember_project_fact")
    rename_room_tool = _tool_by_name("rename_room")
    set_room_type_tool = _tool_by_name("set_room_type")

    room_fact_result = room_fact_tool.function(
        ctx,
        FactNoteInput(
            key="avoid_low_tables",
            kind="constraint",
            summary="Avoid recommending low tables because the user has toddlers.",
            source="Low tables feel risky around the toddlers.",
        ),
    )
    project_fact_result = project_fact_tool.function(
        ctx,
        FactNoteInput(
            key="avoid_drilling",
            kind="constraint",
            summary="User cannot drill into the walls across the project.",
            source="The rental does not allow drilling.",
        ),
    )
    rename_room_tool.function(ctx, RenameRoomInput(title="Son's room"))
    set_room_type_tool.function(ctx, SetRoomTypeInput(room_type="bedroom"))

    room_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)

    assert room_fact_result.fact.scope == "room"
    assert project_fact_result.fact.scope == "project"
    assert room_context.room_identity.title == "Son's room"
    assert room_context.room_identity.room_type == "bedroom"
    assert [item.value for item in room_context.room_facts] == ["avoid_low_tables"]
    assert [item.value for item in room_context.project_facts] == ["avoid_drilling"]
    assert deps.state.room_title == "Son's room"
    assert deps.state.room_type == "bedroom"
    assert deps.state.project_id == room_context.room_identity.project_id


def test_shared_context_read_tools_return_room_wide_artifacts(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    context_repository = ContextFactRepository(runtime.session_factory)
    asset_repository = AssetRepository(runtime.session_factory)
    analysis_repository = AnalysisRepository(runtime.session_factory)
    floor_plan_repository = FloorPlanRepository(runtime.session_factory)
    room_3d_repository = Room3DRepository(runtime.session_factory)
    search_repository = SearchRepository(runtime.session_factory)
    attachment_store = AttachmentStore(tmp_path / "attachments", asset_repository=asset_repository)

    _seed_shared_room_context(context_repository)
    artifacts = _seed_shared_read_artifacts(
        attachment_store=attachment_store,
        analysis_repository=analysis_repository,
        floor_plan_repository=floor_plan_repository,
        room_3d_repository=room_3d_repository,
        search_repository=search_repository,
    )

    deps = SearchAgentDeps(
        runtime=cast("ChatRuntime", runtime),
        attachment_store=attachment_store,
        state=SearchAgentState(
            room_id=DEFAULT_DEV_ROOM_ID,
            thread_id="thread-reader",
            run_id="run-read",
        ),
    )
    ctx = RunContext[SearchAgentDeps](
        deps=deps,
        model=TestModel(),
        usage=RunUsage(),
        prompt="read shared room context",
        tool_name="get_room_facts",
    )

    room_facts = _tool_by_name("get_room_facts").function(ctx)
    project_facts = _tool_by_name("get_project_facts").function(ctx)
    room_images = _tool_by_name("list_room_images").function(ctx)
    latest_floor_plan = _tool_by_name("get_latest_floor_plan").function(ctx)
    floor_plan_revisions = _tool_by_name("list_floor_plan_revisions").function(ctx)
    image_analyses = _tool_by_name("list_room_image_analyses").function(ctx)
    room_3d_snapshots = _tool_by_name("list_room_3d_snapshots").function(ctx)
    bundle_proposals = _tool_by_name("list_room_bundle_proposals").function(ctx)

    assert [item.value for item in room_facts] == ["avoid_low_tables"]
    assert [item.value for item in project_facts] == ["avoid_drilling"]
    assert deps.state.project_id == DEFAULT_DEV_PROJECT_ID
    assert deps.state.room_title == "Son's room"
    assert deps.state.room_type == "bedroom"
    assert [item.attachment.attachment_id for item in room_images] == [
        artifacts.second_image.ref.attachment_id,
        artifacts.first_image.ref.attachment_id,
    ]
    assert latest_floor_plan is not None
    assert latest_floor_plan.revision == 1
    assert latest_floor_plan.png_attachment is not None
    assert (
        latest_floor_plan.png_attachment.attachment_id == artifacts.floor_plan_png.ref.attachment_id
    )
    assert latest_floor_plan.svg_attachment is not None
    assert (
        latest_floor_plan.svg_attachment.attachment_id == artifacts.floor_plan_svg.ref.attachment_id
    )
    assert [item.revision for item in floor_plan_revisions] == [1]
    assert image_analyses[0].thread_id == "thread-followup"
    assert [item.attachment_id for item in image_analyses[0].input_images] == [
        artifacts.first_image.ref.attachment_id,
        artifacts.second_image.ref.attachment_id,
    ]
    assert room_3d_snapshots[0].room_3d_asset_id == artifacts.room_3d_asset_id
    assert room_3d_snapshots[0].snapshot_image is not None
    assert (
        room_3d_snapshots[0].snapshot_image.attachment_id
        == artifacts.snapshot_image.ref.attachment_id
    )
    assert [item.bundle_id for item in bundle_proposals] == ["bundle-1"]


def test_ag_ui_route_does_not_extract_facts_from_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    repository = ContextFactRepository(runtime.session_factory)
    captured_prompts: list[str] = []

    def _build_agent(
        _name: str,
        *,
        explicit_model: str | None = None,
    ) -> Agent[SearchAgentDeps, str]:
        _ = explicit_model
        return _build_capturing_search_agent(captured_prompts)

    monkeypatch.setattr(
        "ikea_agent.chat_app.main.list_agent_catalog",
        lambda: [
            {
                "name": "search",
                "description": "Test search agent",
                "agent_key": "agent_search",
                "ag_ui_path": "/ag-ui/agents/search",
                "web_path": "/agents/search/chat/",
            }
        ],
    )
    monkeypatch.setattr("ikea_agent.chat_app.main.build_agent_ag_ui_agent", _build_agent)

    client = TestClient(
        create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False, mount_ag_ui=True)
    )

    response = client.post(
        "/ag-ui/agents/search",
        json=_payload(
            thread_id="thread-pref",
            run_id="run-1",
            text=(
                "Could you make me a second bundle with adhesive and shelves? "
                "We have a toddler and low tables feel risky."
            ),
        ),
    )

    room_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)
    assert response.status_code == 200
    assert room_context.room_facts == []
    assert room_context.project_facts == []


def test_ag_ui_route_hydrates_room_and_project_facts_into_later_agent_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    repository = ContextFactRepository(runtime.session_factory)
    captured_prompts: list[str] = []

    def _build_agent(
        _name: str,
        *,
        explicit_model: str | None = None,
    ) -> Agent[SearchAgentDeps, str]:
        _ = explicit_model
        return _build_capturing_search_agent(captured_prompts)

    monkeypatch.setattr(
        "ikea_agent.chat_app.main.list_agent_catalog",
        lambda: [
            {
                "name": "search",
                "description": "Test search agent",
                "agent_key": "agent_search",
                "ag_ui_path": "/ag-ui/agents/search",
                "web_path": "/agents/search/chat/",
            }
        ],
    )
    monkeypatch.setattr("ikea_agent.chat_app.main.build_agent_ag_ui_agent", _build_agent)

    room_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)
    repository.rename_room(room_id=DEFAULT_DEV_ROOM_ID, title="Living room")
    repository.set_room_type(room_id=DEFAULT_DEV_ROOM_ID, room_type="living_room")
    repository.upsert_room_facts(
        room_id=DEFAULT_DEV_ROOM_ID,
        run_id=None,
        facts=[
            note_to_known_fact_input(
                FactNoteInput(
                    key="user_has_toddlers",
                    kind="constraint",
                    summary="User has toddlers, keep things elevated.",
                    source="Low tables feel risky around the toddlers.",
                )
            )
        ],
    )
    repository.upsert_project_facts(
        project_id=room_context.room_identity.project_id,
        run_id=None,
        facts=[
            note_to_known_fact_input(
                FactNoteInput(
                    key="avoid_drilling",
                    kind="constraint",
                    summary="User cannot drill into the walls.",
                    source="This rental does not allow drilling.",
                )
            )
        ],
    )

    client = TestClient(
        create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False, mount_ag_ui=True)
    )
    response = client.post(
        "/ag-ui/agents/search",
        json=_payload(
            thread_id="thread-pref",
            run_id="run-2",
            text="Could you suggest a safer second option for the same room?",
        ),
    )

    assert response.status_code == 200
    assert captured_prompts
    assert "remember_room_fact" in captured_prompts[-1]
    assert "remember_project_fact" in captured_prompts[-1]
    assert "rename_room" in captured_prompts[-1]
    assert "set_room_type" in captured_prompts[-1]
    assert "Current room profile:" in captured_prompts[-1]
    assert "Living room" in captured_prompts[-1]
    assert "Room facts:" in captured_prompts[-1]
    assert "Project facts:" in captured_prompts[-1]
    assert "User has toddlers, keep things elevated." in captured_prompts[-1]
    assert "User cannot drill into the walls." in captured_prompts[-1]
