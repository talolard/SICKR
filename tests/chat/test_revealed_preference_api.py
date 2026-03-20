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
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat_app.main import create_app
from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.ownership import (
    DEFAULT_DEV_PROJECT_ID,
    DEFAULT_DEV_ROOM_ID,
    ensure_default_dev_hierarchy_for_session_factory,
)
from ikea_agent.shared.sqlalchemy_db import create_session_factory
from ikea_agent.tools.facts import (
    FactNoteInput,
    RenameRoomInput,
    SetRoomTypeInput,
    note_to_known_fact_input,
)

KNOWN_FACT_INSTRUCTION: Callable[[RunContext[SearchAgentDeps]], str] = cast(
    "Callable[[RunContext[SearchAgentDeps]], str]", build_known_fact_instruction()
)


@dataclass(frozen=True, slots=True)
class _PersistenceRuntime:
    sqlalchemy_engine: Engine
    session_factory: sessionmaker[Session]


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
