"""AG-UI route registration helpers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic_ai import Agent
from pydantic_ai.ag_ui import handle_ag_ui_request

from ikea_agent.chat.agents.index import AnyAgentDeps, clone_agent_deps_for_request
from ikea_agent.persistence.context_fact_repository import (
    ContextFactRepository,
    RoomContextSnapshot,
)
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)
from ikea_agent.shared.types import KnownFactMemory, RoomType


@dataclass(frozen=True, slots=True)
class AgUiRunContext:
    """Validated durable request context for one AG-UI run."""

    run_id: str
    project_id: str | None
    room_id: str
    room_title: str | None
    room_type: RoomType | None
    thread_id: str
    room_facts: list[KnownFactMemory]
    project_facts: list[KnownFactMemory]


def _load_room_context(
    repository: ContextFactRepository | None,
    *,
    room_id: str,
) -> RoomContextSnapshot | None:
    if repository is None:
        return None
    return repository.load_room_context(room_id=room_id)


def _optional_string(payload: dict[str, object], snake_key: str, camel_key: str) -> str | None:
    value = payload.get(snake_key) or payload.get(camel_key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _required_context_value(
    payload: dict[str, object],
    normalized_state: dict[str, object],
    snake_key: str,
    camel_key: str,
) -> str:
    value = payload.get(snake_key) or payload.get(camel_key)
    if value is None:
        value = normalized_state.get(snake_key) or normalized_state.get(camel_key)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    raise HTTPException(
        status_code=400,
        detail=f"AG-UI requests require explicit `{camel_key}`.",
    )


async def _parse_and_record_run_context(
    request: Request,
    *,
    agent_name: str,
    run_history_repository: RunHistoryRepository | None,
    context_fact_repository: ContextFactRepository | None,
) -> AgUiRunContext:
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="AG-UI payload must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="AG-UI payload must be a JSON object.")

    state_payload = payload.get("state")
    normalized_state: dict[str, object] = (
        dict(state_payload) if isinstance(state_payload, dict) else {}
    )
    run_id = _optional_string(payload, "run_id", "runId") or f"agui-{uuid4().hex[:16]}"
    room_id = _required_context_value(payload, normalized_state, "room_id", "roomId")
    thread_id = _required_context_value(payload, normalized_state, "thread_id", "threadId")
    parent_run_id = _optional_string(payload, "parent_run_id", "parentRunId")
    message_payload = payload.get("messages")
    messages = message_payload if isinstance(message_payload, list) else []
    structured_messages = [item for item in messages if isinstance(item, dict)]
    user_prompt_text = extract_last_user_prompt(structured_messages)
    try:
        room_context = _load_room_context(context_fact_repository, room_id=room_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run_history_repository is not None:
        try:
            run_history_repository.record_run_start(
                room_id=room_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                parent_run_id=parent_run_id,
                user_prompt_text=user_prompt_text,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    normalized_state["room_id"] = room_id
    normalized_state["thread_id"] = thread_id
    normalized_state["run_id"] = run_id
    normalized_state["project_id"] = (
        room_context.room_identity.project_id if room_context is not None else None
    )
    normalized_state["room_title"] = (
        room_context.room_identity.title if room_context is not None else None
    )
    normalized_state["room_type"] = (
        room_context.room_identity.room_type if room_context is not None else None
    )
    normalized_state["room_facts"] = (
        [item.model_dump(mode="json") for item in room_context.room_facts]
        if room_context is not None
        else []
    )
    normalized_state["project_facts"] = (
        [item.model_dump(mode="json") for item in room_context.project_facts]
        if room_context is not None
        else []
    )
    payload["state"] = normalized_state
    request._body = json.dumps(payload).encode("utf-8")  # type: ignore[attr-defined]
    return AgUiRunContext(
        run_id=run_id,
        project_id=room_context.room_identity.project_id if room_context is not None else None,
        room_id=room_id,
        room_title=room_context.room_identity.title if room_context is not None else None,
        room_type=room_context.room_identity.room_type if room_context is not None else None,
        thread_id=thread_id,
        room_facts=room_context.room_facts if room_context is not None else [],
        project_facts=room_context.project_facts if room_context is not None else [],
    )


def _build_on_complete(
    run_history_repository: RunHistoryRepository | None,
    *,
    run_id: str,
) -> Callable[[object], Awaitable[None]]:
    async def _on_complete(_result: object) -> None:
        if run_history_repository is not None:
            run_history_repository.record_run_complete(run_id=run_id)

    return _on_complete


def _populate_agent_state(
    deps: AnyAgentDeps,
    *,
    project_id: str | None,
    room_id: str,
    room_title: str | None,
    room_type: RoomType | None,
    thread_id: str,
    run_id: str,
    room_facts: list[KnownFactMemory],
    project_facts: list[KnownFactMemory],
) -> None:
    deps.state.project_id = project_id
    deps.state.room_id = room_id
    deps.state.room_title = room_title
    deps.state.room_type = room_type
    deps.state.thread_id = thread_id
    deps.state.run_id = run_id
    deps.state.room_facts = list(room_facts)
    deps.state.project_facts = list(project_facts)


def _register_ag_ui_routes(
    app: FastAPI,
    *,
    agents: dict[str, Agent[object, str]],
    deps_by_agent: dict[str, AnyAgentDeps],
    run_history_repository: RunHistoryRepository | None,
    context_fact_repository: ContextFactRepository | None,
) -> None:
    @app.post("/ag-ui/agents/{agent_name}")
    @app.post("/ag-ui/agents/{agent_name}/")
    async def run_agent_ag_ui(request: Request, agent_name: str) -> Response:
        agent = agents.get(agent_name)
        base_deps = deps_by_agent.get(agent_name)
        if agent is None or base_deps is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent `{agent_name}`.")

        deps = clone_agent_deps_for_request(base_deps)
        context = await _parse_and_record_run_context(
            request,
            agent_name=agent_name,
            run_history_repository=run_history_repository,
            context_fact_repository=context_fact_repository,
        )
        _populate_agent_state(
            deps,
            project_id=context.project_id,
            room_id=context.room_id,
            room_title=context.room_title,
            room_type=context.room_type,
            thread_id=context.thread_id,
            run_id=context.run_id,
            room_facts=context.room_facts,
            project_facts=context.project_facts,
        )
        on_complete = _build_on_complete(run_history_repository, run_id=context.run_id)
        try:
            with deps.attachment_store.bind_context(
                room_id=context.room_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
            ):
                return await handle_ag_ui_request(
                    agent,
                    request,
                    deps=deps,
                    on_complete=on_complete,
                )
        except Exception as exc:
            if run_history_repository is not None:
                run_history_repository.record_run_failed(
                    run_id=context.run_id,
                    error_message=str(exc),
                )
            raise
