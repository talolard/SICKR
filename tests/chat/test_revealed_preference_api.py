from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import build_search_toolset
from ikea_agent.chat.agents.shared import (
    build_preference_instruction,
    build_remember_preference_tool,
)
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat_app.main import create_app
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.revealed_preference_repository import RevealedPreferenceRepository
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine, create_session_factory
from ikea_agent.tools.preferences import PreferenceNoteInput, note_to_memory_input

PREFERENCE_INSTRUCTION: Callable[[RunContext[SearchAgentDeps]], str] = cast(
    "Callable[[RunContext[SearchAgentDeps]], str]", build_preference_instruction()
)


@dataclass(frozen=True, slots=True)
class _PersistenceRuntime:
    sqlalchemy_engine: Engine
    session_factory: sessionmaker[Session]


@pytest.fixture(autouse=True)
def _set_fake_google_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-api-key")


def _runtime(tmp_path: Path) -> _PersistenceRuntime:
    engine = create_duckdb_engine(str(tmp_path / "revealed_preference_api_test.duckdb"))
    ensure_persistence_schema(engine)
    return _PersistenceRuntime(
        sqlalchemy_engine=engine,
        session_factory=create_session_factory(engine),
    )


def _payload(*, thread_id: str, run_id: str, text: str) -> dict[str, object]:
    return {
        "threadId": thread_id,
        "runId": run_id,
        "state": {},
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
        raise AssertionError("non-stream function path should not be called")

    async def _stream(
        messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> AsyncIterator[str]:
        captured_prompts.append(_flatten_message_text(messages))
        yield "memory-aware-response"

    return Agent(
        model=FunctionModel(
            function=_function,
            stream_function=_stream,
            model_name="preference-test-agent",
        ),
        deps_type=SearchAgentDeps,
        output_type=str,
        instructions=["Base search instructions.", PREFERENCE_INSTRUCTION],
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


def test_remember_preference_tool_persists_summary_and_updates_state(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    repository = RevealedPreferenceRepository(runtime.session_factory)
    attachment_store = AttachmentStore(tmp_path / "attachments")
    deps = SearchAgentDeps(
        runtime=cast("ChatRuntime", runtime),
        attachment_store=attachment_store,
        state=SearchAgentState(thread_id="thread-pref", run_id="run-1"),
    )
    ctx = RunContext[SearchAgentDeps](
        deps=deps,
        model=TestModel(),
        usage=RunUsage(),
        prompt="remember preference",
        tool_name="remember_preference",
    )

    tool = build_remember_preference_tool()
    result = tool.function(
        ctx,
        PreferenceNoteInput(
            key="user_has_toddlers",
            kind="constraint",
            summary="User has toddlers, keep things elevated.",
            source="They said low tables feel risky around the toddlers.",
        ),
    )

    stored = repository.list_preferences(thread_id="thread-pref")

    assert result.memory.summary == "User has toddlers, keep things elevated."
    assert len(stored) == 1
    assert stored[0].signal_key == "agent_note"
    assert stored[0].value == "user_has_toddlers"
    assert deps.state.revealed_preferences == stored


def test_ag_ui_route_does_not_extract_preferences_from_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    repository = RevealedPreferenceRepository(runtime.session_factory)
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

    assert response.status_code == 200
    assert repository.list_preferences(thread_id="thread-pref") == []


def test_ag_ui_route_hydrates_revealed_preferences_into_later_agent_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    repository = RevealedPreferenceRepository(runtime.session_factory)
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

    repository.upsert_preferences(
        thread_id="thread-pref",
        run_id=None,
        preferences=[
            note_to_memory_input(
                PreferenceNoteInput(
                    key="user_has_toddlers",
                    kind="constraint",
                    summary="User has toddlers, keep things elevated.",
                    source="Low tables feel risky around the toddlers.",
                )
            ),
            note_to_memory_input(
                PreferenceNoteInput(
                    key="avoid_drilling",
                    kind="constraint",
                    summary="User cannot drill into the walls.",
                    source="This rental does not allow drilling.",
                )
            ),
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
            text="Could you suggest a safer second option for the same hallway thread?",
        ),
    )

    assert response.status_code == 200
    assert captured_prompts
    assert "remember_preference" in captured_prompts[-1]
    assert (
        "Thread-scoped revealed preferences from prior conversation turns:" in captured_prompts[-1]
    )
    assert "User has toddlers, keep things elevated." in captured_prompts[-1]
    assert "User cannot drill into the walls." in captured_prompts[-1]
