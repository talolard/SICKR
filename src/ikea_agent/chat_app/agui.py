"""AG-UI route registration helpers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from logging import getLogger
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic_ai import Agent
from pydantic_ai.ag_ui import handle_ag_ui_request

from ikea_agent.chat.agents.index import AnyAgentDeps
from ikea_agent.persistence.revealed_preference_repository import (
    RevealedPreferenceRepository,
)
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)
from ikea_agent.shared.types import RevealedPreferenceMemory

logger = getLogger(__name__)


def _list_revealed_preferences(
    repository: RevealedPreferenceRepository | None,
    *,
    thread_id: str,
) -> list[RevealedPreferenceMemory]:
    if repository is None:
        return []
    return repository.list_preferences(thread_id=thread_id)


async def _parse_and_record_run_context(
    request: Request,
    *,
    agent_name: str,
    run_history_repository: RunHistoryRepository | None,
    revealed_preference_repository: RevealedPreferenceRepository | None,
) -> tuple[str, str]:
    body = await request.body()
    run_id = f"agui-{uuid4().hex[:16]}"
    thread_id = "anonymous-thread"
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
        run_id = str(payload.get("run_id") or payload.get("runId") or run_id)
        thread_id = str(payload.get("thread_id") or payload.get("threadId") or thread_id)
        parent_run_id = payload.get("parent_run_id") or payload.get("parentRunId")
        parent_run_id_value = str(parent_run_id) if parent_run_id is not None else None
        message_payload = payload.get("messages")
        messages = message_payload if isinstance(message_payload, list) else []
        structured_messages = [item for item in messages if isinstance(item, dict)]
        user_prompt_text = extract_last_user_prompt(structured_messages)
        revealed_preferences = _list_revealed_preferences(
            revealed_preference_repository,
            thread_id=thread_id,
        )
        if run_history_repository is not None:
            run_history_repository.record_run_start(
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                parent_run_id=parent_run_id_value,
                user_prompt_text=user_prompt_text,
            )
        state_payload = payload.get("state")
        normalized_state: dict[str, object] = (
            dict(state_payload) if isinstance(state_payload, dict) else {}
        )
        normalized_state["thread_id"] = thread_id
        normalized_state["run_id"] = run_id
        normalized_state["revealed_preferences"] = [
            item.model_dump(mode="json") for item in revealed_preferences
        ]
        payload["state"] = normalized_state
        request._body = json.dumps(payload).encode("utf-8")  # type: ignore[attr-defined]
    except Exception:
        logger.debug("failed_to_parse_ag_ui_payload_for_run_history", exc_info=True)
    return run_id, thread_id


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
    thread_id: str,
    run_id: str,
    revealed_preference_repository: RevealedPreferenceRepository | None,
) -> None:
    deps.state.thread_id = thread_id
    deps.state.run_id = run_id
    deps.state.revealed_preferences = _list_revealed_preferences(
        revealed_preference_repository,
        thread_id=thread_id,
    )


def _register_ag_ui_routes(
    app: FastAPI,
    *,
    agents: dict[str, Agent[object, str]],
    deps_by_agent: dict[str, AnyAgentDeps],
    run_history_repository: RunHistoryRepository | None,
    revealed_preference_repository: RevealedPreferenceRepository | None,
) -> None:
    @app.post("/ag-ui/agents/{agent_name}")
    @app.post("/ag-ui/agents/{agent_name}/")
    async def run_agent_ag_ui(request: Request, agent_name: str) -> Response:
        agent = agents.get(agent_name)
        deps = deps_by_agent.get(agent_name)
        if agent is None or deps is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent `{agent_name}`.")

        run_id, thread_id = await _parse_and_record_run_context(
            request,
            agent_name=agent_name,
            run_history_repository=run_history_repository,
            revealed_preference_repository=revealed_preference_repository,
        )
        _populate_agent_state(
            deps,
            thread_id=thread_id,
            run_id=run_id,
            revealed_preference_repository=revealed_preference_repository,
        )
        on_complete = _build_on_complete(run_history_repository, run_id=run_id)
        try:
            with deps.attachment_store.bind_context(
                thread_id=deps.state.thread_id or "anonymous-thread",
                run_id=deps.state.run_id,
            ):
                return await handle_ag_ui_request(
                    agent,
                    request,
                    deps=deps,
                    on_complete=on_complete,
                )
        except Exception as exc:
            if run_history_repository is not None:
                run_history_repository.record_run_failed(run_id=run_id, error_message=str(exc))
            raise
