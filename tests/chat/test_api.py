from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat.agents.index import AgentCatalogItem
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app
from ikea_agent.config import get_settings
from ikea_agent.persistence.models import (
    ProjectRecord,
    RoomRecord,
    ThreadRecord,
    UserRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.ownership import (
    DEFAULT_DEV_PROJECT_ID,
    DEFAULT_DEV_ROOM_ID,
    DEFAULT_DEV_USER_ID,
    ensure_default_dev_hierarchy,
)


@dataclass
class _PersistenceRuntimeStub:
    sqlalchemy_engine: object
    session_factory: sessionmaker[Session]


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _set_fake_google_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-api-key")


def _chat_request_payload(user_text: str) -> dict[str, object]:
    return {
        "trigger": "submit-message",
        "id": "run-1",
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "parts": [{"type": "text", "text": user_text}],
            }
        ],
    }


def _ag_ui_request_payload(user_text: str) -> dict[str, object]:
    return {
        "roomId": DEFAULT_DEV_ROOM_ID,
        "threadId": "thread-1",
        "runId": "run-1",
        "state": {
            "room_id": DEFAULT_DEV_ROOM_ID,
            "session_id": "session-test",
        },
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": user_text,
            }
        ],
    }


def _build_stream_only_agent(stream_text: str) -> Agent[object, str]:
    async def _function(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[])

    async def _stream(
        _messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> AsyncIterator[str]:
        yield stream_text

    return Agent(
        model=FunctionModel(
            function=_function,
            stream_function=_stream,
            model_name=f"stream-{stream_text}",
        ),
        deps_type=object,
        output_type=str,
    )


def _runtime_with_persistence(tmp_path: Path) -> _PersistenceRuntimeStub:
    engine = create_sqlite_engine(tmp_path / "app_bootstrap_test.sqlite")
    ensure_persistence_schema(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _PersistenceRuntimeStub(sqlalchemy_engine=engine, session_factory=session_factory)


def test_create_app_without_mount_has_no_custom_routes() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/")
    ag_ui_response = client.get("/ag-ui")

    assert response.status_code == 404
    assert ag_ui_response.status_code == 404


def test_create_app_with_ag_ui_mount_exposes_ag_ui_route() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.post("/ag-ui/agents/floor_plan_intake", json={"messages": []})

    assert response.status_code != 404


def test_agent_catalog_route_lists_registered_agents() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/api/agents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agents"]
    assert any(item["name"] == "floor_plan_intake" for item in payload["agents"])


def test_agent_ag_ui_route_exists() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.post("/ag-ui/agents/floor_plan_intake", json={"messages": []})
    assert response.status_code != 404


def test_agent_ag_ui_route_uses_deterministic_env_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DETERMINISTIC_MODEL_RESPONSE_TEXT",
        "Deterministic smoke response from the local test model.",
    )
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.post(
        "/ag-ui/agents/search",
        json=_ag_ui_request_payload("hello"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "Deterministic smoke response from the local test model." in response.text


def test_agent_ag_ui_route_requires_explicit_room_context() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.post(
        "/ag-ui/agents/search",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [{"id": "message-1", "role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "AG-UI requests require explicit `roomId`."


def test_agent_ag_ui_route_rejects_thread_room_mismatches(tmp_path: Path) -> None:
    runtime = _runtime_with_persistence(tmp_path)
    now = datetime.now(UTC)
    with runtime.session_factory() as session:
        ensure_default_dev_hierarchy(session, now=now)
        session.add(
            RoomRecord(
                room_id="room-other",
                project_id=DEFAULT_DEV_PROJECT_ID,
                title="Other room",
                room_type="office",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ThreadRecord(
                thread_id="thread-1",
                room_id=DEFAULT_DEV_ROOM_ID,
                title="Existing thread",
                status="active",
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
        )
        session.commit()

    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", runtime),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.post(
        "/ag-ui/agents/search",
        json={
            "roomId": "room-other",
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {"room_id": "room-other", "session_id": "session-test"},
            "messages": [{"id": "message-1", "role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Thread `thread-1` belongs to room `room-dev-default`, not `room-other`."
    )


def test_create_app_seeds_default_dev_hierarchy_for_persistence_runtime(tmp_path: Path) -> None:
    runtime = _runtime_with_persistence(tmp_path)

    create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False, mount_ag_ui=False)

    with runtime.session_factory() as session:
        user_ids = session.execute(select(UserRecord.user_id)).scalars().all()
        project_ids = session.execute(select(ProjectRecord.project_id)).scalars().all()
        room_ids = session.execute(select(RoomRecord.room_id)).scalars().all()

    assert user_ids == [DEFAULT_DEV_USER_ID]
    assert project_ids == [DEFAULT_DEV_PROJECT_ID]
    assert room_ids == [DEFAULT_DEV_ROOM_ID]


def test_agent_metadata_route_returns_prompt_and_tools() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/api/agents/floor_plan_intake/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt_markdown"]
    assert "render_floor_plan" in payload["tools"]


def test_agent_web_chat_mount_boots_and_dispatches_to_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _stubbed_ui_html(_html_source: str | Path | None = None) -> bytes:
        return b"<!doctype html><html><body>agent-ui</body></html>"

    agent_agent = _build_stream_only_agent("agent-stream")
    catalog_item: AgentCatalogItem = {
        "name": "floor_plan_intake",
        "description": "Test agent",
        "agent_key": "agent_floor_plan_intake",
        "ag_ui_path": "/ag-ui/agents/floor_plan_intake",
        "web_path": "/agents/floor_plan_intake/chat/",
    }

    def _build_agent(
        name: str,
        *,
        explicit_model: str | None = None,
    ) -> Agent[object, str]:
        _ = name
        _ = explicit_model
        return agent_agent

    monkeypatch.setattr("pydantic_ai.ui._web.app._get_ui_html", _stubbed_ui_html)
    monkeypatch.setattr(
        "ikea_agent.chat_app.main.list_agent_catalog",
        lambda: [catalog_item],
    )
    monkeypatch.setattr(
        "ikea_agent.chat_app.main.build_agent_ag_ui_agent",
        _build_agent,
    )

    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=True,
            mount_ag_ui=False,
        )
    )
    payload = _chat_request_payload("route-check")

    boot_response = client.get("/agents/floor_plan_intake/chat/")
    agent_response = client.post("/agents/floor_plan_intake/chat/api/chat", json=payload)
    main_response = client.post("/api/chat", json=payload)

    assert boot_response.status_code == 200
    assert "agent-ui" in boot_response.text
    assert agent_response.status_code == 200
    assert main_response.status_code == 404
    assert agent_response.headers["content-type"].startswith("text/event-stream")
    assert "agent-stream" in agent_response.text


def test_function_model_web_adapter_uses_streaming_path_for_chat_dispatch(
    tmp_path: Path,
) -> None:
    ui_html = tmp_path / "chat-ui.html"
    ui_html.write_text("<!doctype html><html><body>stream-ui</body></html>", encoding="utf-8")

    stream_calls = {"count": 0}

    async def _function(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[])

    async def _stream(
        _messages: list[ModelMessage],
        _info: AgentInfo,
    ) -> AsyncIterator[str]:
        stream_calls["count"] += 1
        yield "stream-only-response"

    stream_agent = Agent(
        model=FunctionModel(
            function=_function,
            stream_function=_stream,
            model_name="stream-only-test-agent",
        ),
        deps_type=type(None),
        output_type=str,
    )
    client = TestClient(stream_agent.to_web(deps=None, html_source=ui_html))

    response = client.post("/api/chat", json=_chat_request_payload("stream-check"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "stream-only-response" in response.text
    assert stream_calls["count"] == 1


def test_attachment_upload_and_fetch_round_trip() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"fake-image-bytes",
        headers={"content-type": "image/png", "x-filename": "room.png"},
    )

    assert upload_response.status_code == 200
    attachment_ref = upload_response.json()
    assert attachment_ref["attachment_id"]
    assert attachment_ref["uri"].startswith("/attachments/")

    download_response = client.get(attachment_ref["uri"])
    assert download_response.status_code == 200
    assert download_response.content == b"fake-image-bytes"
    assert download_response.headers["content-type"].startswith("image/png")


def test_attachment_upload_requires_room_and_thread_context_when_persistence_is_enabled(
    tmp_path: Path,
) -> None:
    runtime = _runtime_with_persistence(tmp_path)
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"fake-image-bytes",
        headers={"content-type": "image/png", "x-filename": "room.png"},
    )

    assert upload_response.status_code == 400
    assert upload_response.json()["detail"] == (
        "Attachment uploads require explicit x-room-id and x-thread-id headers."
    )


def test_attachment_upload_rejects_unsupported_type() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"not-an-image",
        headers={"content-type": "application/pdf"},
    )

    assert upload_response.status_code == 415
