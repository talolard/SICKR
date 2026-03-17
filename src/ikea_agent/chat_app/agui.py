"""AG-UI route registration and SSE capture helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Awaitable, Callable
from logging import getLogger
from typing import Protocol, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic_ai import Agent
from pydantic_ai.ag_ui import handle_ag_ui_request

from ikea_agent.chat.agents.index import AnyAgentDeps
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)

logger = getLogger(__name__)


class _ArchivedMessagesResult(Protocol):
    def all_messages_json(self) -> bytes: ...

    def new_messages_json(self) -> bytes: ...


def _iter_sse_blocks(raw_stream: bytes) -> list[str]:
    decoded = raw_stream.decode("utf-8", errors="replace")
    return [block for block in decoded.split("\n\n") if block.strip()]


def _parse_sse_payload(raw_data: str) -> object:
    if not raw_data:
        return {}
    try:
        return json.loads(raw_data)
    except json.JSONDecodeError:
        return raw_data


def _parse_sse_block(block: str) -> tuple[str | None, object]:
    event_name: str | None = None
    data_parts: list[str] = []
    for line in block.splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ").strip()
        elif line.startswith("data: "):
            data_parts.append(line.removeprefix("data: "))
    raw_data = "\n".join(data_parts).strip()
    return event_name, _parse_sse_payload(raw_data)


def _build_trace_entry(
    *,
    agent_name: str,
    thread_id: str,
    run_id: str,
    index: int,
    event_name: str | None,
    parsed_data: object,
) -> dict[str, object]:
    event_type = event_name or "message"
    timestamp: int | None = None
    if isinstance(parsed_data, dict):
        event_type = str(parsed_data.get("type") or event_type)
        timestamp_obj = parsed_data.get("timestamp")
        if isinstance(timestamp_obj, int):
            timestamp = timestamp_obj
    return {
        "id": f"agent_{agent_name}:{index}",
        "agentId": f"agent_{agent_name}",
        "threadId": thread_id,
        "runId": run_id,
        "type": event_type,
        "timestamp": timestamp,
        "payload": parsed_data,
    }


def _serialize_agui_event_trace(
    *,
    raw_stream: bytes,
    agent_name: str,
    thread_id: str,
    run_id: str,
) -> str:
    """Normalize one outbound AG-UI SSE stream into canonical JSON events."""

    entries = [
        _build_trace_entry(
            agent_name=agent_name,
            thread_id=thread_id,
            run_id=run_id,
            index=index,
            event_name=event_name,
            parsed_data=parsed_data,
        )
        for index, block in enumerate(_iter_sse_blocks(raw_stream), start=1)
        for event_name, parsed_data in [_parse_sse_block(block)]
    ]
    return json.dumps(entries, ensure_ascii=True)


def _register_ag_ui_routes(  # noqa: C901
    app: FastAPI,
    *,
    agents: dict[str, Agent[object, str]],
    deps_by_agent: dict[str, AnyAgentDeps],
    run_history_repository: RunHistoryRepository | None,
) -> None:
    async def _parse_and_record_run_context(
        request: Request,
        *,
        agent_name: str,
    ) -> tuple[bytes, str, str]:
        body = await request.body()
        run_id = f"agui-{uuid4().hex[:16]}"
        thread_id = "anonymous-thread"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            run_id = str(payload.get("run_id") or run_id)
            thread_id = str(payload.get("thread_id") or thread_id)
            parent_run_id = payload.get("parent_run_id")
            parent_run_id_value = str(parent_run_id) if isinstance(parent_run_id, str) else None
            message_payload = payload.get("messages")
            messages = message_payload if isinstance(message_payload, list) else []
            user_prompt_text = extract_last_user_prompt(
                [item for item in messages if isinstance(item, dict)]
            )
            if run_history_repository is not None:
                run_history_repository.record_run_start(
                    thread_id=thread_id,
                    run_id=run_id,
                    agent_name=agent_name,
                    parent_run_id=parent_run_id_value,
                    user_prompt_text=user_prompt_text,
                    agui_input_messages_json=json.dumps(messages),
                )
        except Exception:
            # If request parsing fails, proceed with AG-UI normal error semantics.
            logger.debug("failed_to_parse_ag_ui_payload_for_run_history", exc_info=True)
        return body, run_id, thread_id

    def _build_on_complete(run_id: str) -> Callable[[_ArchivedMessagesResult], Awaitable[None]]:
        async def _on_complete(result: _ArchivedMessagesResult) -> None:
            if run_history_repository is not None:
                run_history_repository.record_run_complete(
                    run_id=run_id,
                    pydantic_all_messages_json=result.all_messages_json(),
                    pydantic_new_messages_json=result.new_messages_json(),
                )

        return _on_complete

    @app.post("/ag-ui/agents/{agent_name}")
    @app.post("/ag-ui/agents/{agent_name}/")
    async def run_agent_ag_ui(request: Request, agent_name: str) -> Response:
        agent = agents.get(agent_name)
        deps = deps_by_agent.get(agent_name)
        if agent is None or deps is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent `{agent_name}`.")

        _body, run_id, thread_id = await _parse_and_record_run_context(
            request,
            agent_name=agent_name,
        )
        deps.state.thread_id = thread_id
        deps.state.run_id = run_id
        on_complete = _build_on_complete(run_id)
        try:
            with deps.attachment_store.bind_context(
                thread_id=deps.state.thread_id or "anonymous-thread",
                run_id=deps.state.run_id,
            ):
                response = await handle_ag_ui_request(
                    agent,
                    request,
                    deps=deps,
                    on_complete=on_complete,
                )
                if (
                    run_history_repository is None
                    or not response.headers.get("content-type", "").startswith("text/event-stream")
                    or not hasattr(response, "body_iterator")
                ):
                    return response

                history_repository = run_history_repository
                body_iterator = cast("AsyncIterable[bytes]", response.body_iterator)
                captured_chunks: list[bytes] = []

                async def _capture_body() -> AsyncIterable[bytes]:
                    try:
                        async for chunk in body_iterator:
                            chunk_bytes = (
                                chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8")
                            )
                            captured_chunks.append(chunk_bytes)
                            yield chunk
                    finally:
                        history_repository.record_run_event_trace(
                            run_id=run_id,
                            agui_event_trace_json=_serialize_agui_event_trace(
                                raw_stream=b"".join(captured_chunks),
                                agent_name=agent_name,
                                thread_id=thread_id,
                                run_id=run_id,
                            ),
                        )

                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() != "content-length"
                }
                return StreamingResponse(
                    _capture_body(),
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type,
                    background=response.background,
                )
        except Exception as exc:
            if run_history_repository is not None:
                run_history_repository.record_run_failed(run_id=run_id, error_message=str(exc))
            raise
