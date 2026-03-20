from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat.agents.index import AgentCatalogItem
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import (
    create_app,
)
from ikea_agent.config import get_settings
from ikea_agent.integrations.beads_cli import BeadsTraceIssueCreator, BeadsTraceIssueResult
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.run_history_repository import RunHistoryRepository
from ikea_agent.shared.sqlalchemy_db import create_session_factory


@dataclass(frozen=True, slots=True)
class _PersistenceRuntime:
    sqlalchemy_engine: Engine
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
        "threadId": "thread-1",
        "runId": "run-1",
        "state": {},
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


def test_attachment_upload_rejects_unsupported_type() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"not-an-image",
        headers={"content-type": "application/pdf"},
    )

    assert upload_response.status_code == 415


def _persistence_runtime(tmp_path: Path) -> _PersistenceRuntime:
    engine = create_sqlite_engine(tmp_path / "trace_route_test.sqlite")
    ensure_persistence_schema(engine)
    session_factory = create_session_factory(engine)
    return _PersistenceRuntime(sqlalchemy_engine=engine, session_factory=session_factory)


def test_trace_report_route_is_not_registered_when_disabled(tmp_path: Path) -> None:
    runtime = _persistence_runtime(tmp_path)
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    response = client.post("/api/traces", json={})

    assert response.status_code == 404


def test_trace_report_route_persists_bundle_and_returns_beads_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _persistence_runtime(tmp_path)
    repository = RunHistoryRepository(runtime.session_factory)
    repository.record_run_start(
        thread_id="thread-trace",
        run_id="run-trace-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="Find a desk setup.",
        agui_input_messages_json='[{"role":"user","content":"Find a desk setup."}]',
    )
    repository.record_run_complete(
        run_id="run-trace-1",
        pydantic_all_messages_json=b'[{"kind":"request","text":"Find a desk setup."}]',
        pydantic_new_messages_json=b'[{"kind":"response","text":"Here are options."}]',
    )
    repository.record_run_event_trace(
        run_id="run-trace-1",
        agui_event_trace_json='[{"type":"RUN_STARTED"},{"type":"RUN_FINISHED"}]',
    )

    monkeypatch.setenv("TRACE_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("TRACE_ROOT_DIR", str(tmp_path / "traces"))
    monkeypatch.setattr(
        BeadsTraceIssueCreator,
        "create_trace_epic_and_task",
        lambda *_args, **_kwargs: BeadsTraceIssueResult(
            epic_id="trace-epic-1", task_id="trace-epic-1.1"
        ),
    )
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    response = client.post(
        "/api/traces",
        json={
            "title": "Investigate search latency",
            "description": "The search agent took too long to answer.",
            "thread_id": "thread-trace",
            "agent_name": "search",
            "page_url": "http://localhost:3000/agents/search",
            "user_agent": "pytest",
            "include_console_log": True,
            "console_log": '[{"level":"info","args":["hello"]}]',
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"].startswith("investigate_search_latency--")
    assert payload["status"] == "saved_and_linked"
    assert payload["beads_epic_id"] == "trace-epic-1"
    assert payload["beads_task_id"] == "trace-epic-1.1"

    trace_dir = Path(payload["directory"])
    assert (trace_dir / "metadata.json").exists()
    assert (trace_dir / "trace.json").exists()
    assert (trace_dir / "report.md").exists()

    markdown = (trace_dir / "report.md").read_text(encoding="utf-8")
    assert "Investigate search latency" in markdown
    assert "trace.json" in markdown


def test_trace_report_route_lists_recent_bundles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _persistence_runtime(tmp_path)
    monkeypatch.setenv("TRACE_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("TRACE_ROOT_DIR", str(tmp_path / "traces"))
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    first_dir = tmp_path / "traces" / "trace-one"
    first_dir.mkdir(parents=True)
    (first_dir / "metadata.json").write_text(
        json.dumps(
            {
                "trace_id": "trace-one",
                "title": "First trace",
                "created_at": "2026-03-11T10:00:00Z",
                "thread_id": "thread-a",
                "agent_name": "search",
            }
        ),
        encoding="utf-8",
    )
    second_dir = tmp_path / "traces" / "trace-two"
    second_dir.mkdir(parents=True)
    (second_dir / "metadata.json").write_text(
        json.dumps(
            {
                "trace_id": "trace-two",
                "title": "Second trace",
                "created_at": "2026-03-11T11:00:00Z",
                "thread_id": "thread-b",
                "agent_name": "search",
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/traces/recent?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert [trace["trace_id"] for trace in payload["traces"]] == ["trace-two", "trace-one"]


def test_trace_report_route_redacts_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _persistence_runtime(tmp_path)
    repository = RunHistoryRepository(runtime.session_factory)
    repository.record_run_start(
        thread_id="thread-redact",
        run_id="run-redact-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="token=secret-token",
        agui_input_messages_json='[{"role":"user","content":"password hunter2"}]',
    )
    repository.record_run_complete(
        run_id="run-redact-1",
        pydantic_all_messages_json=b'[{"secret":"api-key-123"}]',
        pydantic_new_messages_json=b'[{"ok":true}]',
    )
    repository.record_run_event_trace(
        run_id="run-redact-1",
        agui_event_trace_json='[{"type":"RUN_FINISHED","payload":{"authorization":"Bearer abc"}}]',
    )

    monkeypatch.setenv("TRACE_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("TRACE_ROOT_DIR", str(tmp_path / "traces"))
    monkeypatch.setattr(
        BeadsTraceIssueCreator,
        "create_trace_epic_and_task",
        lambda *_args, **_kwargs: BeadsTraceIssueResult(
            epic_id="trace-epic-1", task_id="trace-epic-1.1"
        ),
    )
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    response = client.post(
        "/api/traces",
        json={
            "title": "Investigate redaction",
            "thread_id": "thread-redact",
            "agent_name": "search",
            "include_console_log": True,
            "console_log": '[{"token":"abc123"}]',
        },
    )

    assert response.status_code == 200
    payload = response.json()
    trace_dir = Path(payload["directory"])
    trace_json = (trace_dir / "trace.json").read_text(encoding="utf-8")
    console_json = (trace_dir / "console_log.json").read_text(encoding="utf-8")

    assert "secret-token" not in trace_json
    assert "hunter2" not in trace_json
    assert "api-key-123" not in trace_json
    assert "Bearer abc" not in trace_json
    assert "abc123" not in console_json
    assert "[REDACTED]" in trace_json
    assert "[REDACTED]" in console_json


def test_trace_report_route_returns_partial_success_when_beads_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _persistence_runtime(tmp_path)
    repository = RunHistoryRepository(runtime.session_factory)
    repository.record_run_start(
        thread_id="thread-partial",
        run_id="run-partial-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="Need a lamp.",
        agui_input_messages_json='[{"role":"user","content":"Need a lamp."}]',
    )
    repository.record_run_complete(
        run_id="run-partial-1",
        pydantic_all_messages_json=b'[{"kind":"request","text":"Need a lamp."}]',
        pydantic_new_messages_json=b'[{"kind":"response","text":"Here is a lamp."}]',
    )
    repository.record_run_event_trace(
        run_id="run-partial-1",
        agui_event_trace_json='[{"type":"RUN_STARTED"},{"type":"RUN_FINISHED"}]',
    )

    monkeypatch.setenv("TRACE_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("TRACE_ROOT_DIR", str(tmp_path / "traces"))

    def _raise_beads_failure(*_args: object, **_kwargs: object) -> BeadsTraceIssueResult:
        raise RuntimeError("bd create failed")

    monkeypatch.setattr(
        BeadsTraceIssueCreator,
        "create_trace_epic_and_task",
        _raise_beads_failure,
    )
    client = TestClient(create_app(runtime=cast("ChatRuntime", runtime), mount_web_ui=False))

    response = client.post(
        "/api/traces",
        json={
            "title": "Investigate partial success",
            "thread_id": "thread-partial",
            "agent_name": "search",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "saved_without_beads"
    assert payload["beads_epic_id"] is None
    assert payload["beads_task_id"] is None
    trace_dir = Path(payload["directory"])
    assert (trace_dir / "metadata.json").exists()
    assert (trace_dir / "trace.json").exists()
    assert (trace_dir / "report.md").exists()
