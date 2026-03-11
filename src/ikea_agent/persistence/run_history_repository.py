"""Persistence helpers for AG-UI run lifecycle and message archives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Text, select, update
from sqlalchemy import cast as sa_cast
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, MessageArchiveRecord, ThreadRecord


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RunHistoryRepository:
    """Repository for persisting run lifecycle and archived messages."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_run_start(
        self,
        *,
        thread_id: str,
        run_id: str,
        agent_name: str | None,
        parent_run_id: str | None,
        user_prompt_text: str | None,
        agui_input_messages_json: str | None,
    ) -> None:
        """Create/update thread and run rows at AG-UI request start."""

        now = _utcnow()
        with self._session_factory() as session:
            existing_thread_id = session.execute(
                select(ThreadRecord.thread_id).where(ThreadRecord.thread_id == thread_id)
            ).scalar_one_or_none()
            if existing_thread_id is None:
                thread = ThreadRecord(
                    thread_id=thread_id,
                    owner_id=None,
                    title=None,
                    status="active",
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                )
                session.add(thread)
            session.flush()

            existing_run_id = session.execute(
                select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
            ).scalar_one_or_none()
            if existing_run_id is None:
                run = AgentRunRecord(
                    run_id=run_id,
                    thread_id=thread_id,
                    parent_run_id=parent_run_id,
                    agent_name=agent_name,
                    status="started",
                    user_prompt_text=user_prompt_text,
                    error_message=None,
                    started_at=now,
                    ended_at=None,
                )
                session.add(run)
            else:
                session.execute(
                    update(AgentRunRecord)
                    .where(AgentRunRecord.run_id == run_id)
                    .values(
                        thread_id=thread_id,
                        parent_run_id=parent_run_id,
                        agent_name=agent_name,
                        status="started",
                        user_prompt_text=user_prompt_text,
                        error_message=None,
                        started_at=now,
                        ended_at=None,
                    )
                )

            if agui_input_messages_json is not None:
                existing_archive_run_id = session.execute(
                    select(MessageArchiveRecord.run_id).where(MessageArchiveRecord.run_id == run_id)
                ).scalar_one_or_none()
                if existing_archive_run_id is None:
                    archive = MessageArchiveRecord(
                        run_id=run_id,
                        archive_version=1,
                        agui_input_messages_json=agui_input_messages_json,
                        agui_event_trace_json=None,
                        pydantic_all_messages_json=None,
                        pydantic_new_messages_json=None,
                        created_at=now,
                    )
                    session.add(archive)
                else:
                    session.execute(
                        update(MessageArchiveRecord)
                        .where(MessageArchiveRecord.run_id == run_id)
                        .values(agui_input_messages_json=agui_input_messages_json)
                    )

            session.commit()

    def record_run_complete(
        self,
        *,
        run_id: str,
        pydantic_all_messages_json: bytes | None,
        pydantic_new_messages_json: bytes | None,
    ) -> None:
        """Mark run completed and persist message archive payloads."""

        now = _utcnow()
        with self._session_factory() as session:
            existing_run_id = session.execute(
                select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
            ).scalar_one_or_none()
            if existing_run_id is None:
                session.commit()
                return
            session.execute(
                update(AgentRunRecord)
                .where(AgentRunRecord.run_id == run_id)
                .values(status="completed", ended_at=now, error_message=None)
            )

            existing_archive_run_id = session.execute(
                select(MessageArchiveRecord.run_id).where(MessageArchiveRecord.run_id == run_id)
            ).scalar_one_or_none()
            if existing_archive_run_id is None:
                archive = MessageArchiveRecord(
                    run_id=run_id,
                    archive_version=1,
                    agui_input_messages_json=None,
                    agui_event_trace_json=None,
                    pydantic_all_messages_json=(
                        pydantic_all_messages_json.decode("utf-8")
                        if pydantic_all_messages_json is not None
                        else None
                    ),
                    pydantic_new_messages_json=(
                        pydantic_new_messages_json.decode("utf-8")
                        if pydantic_new_messages_json is not None
                        else None
                    ),
                    created_at=now,
                )
                session.add(archive)
            else:
                update_values: dict[str, str] = {}
                if pydantic_all_messages_json is not None:
                    update_values["pydantic_all_messages_json"] = pydantic_all_messages_json.decode(
                        "utf-8"
                    )
                if pydantic_new_messages_json is not None:
                    update_values["pydantic_new_messages_json"] = pydantic_new_messages_json.decode(
                        "utf-8"
                    )
                if update_values:
                    session.execute(
                        update(MessageArchiveRecord)
                        .where(MessageArchiveRecord.run_id == run_id)
                        .values(**update_values)
                    )

            session.commit()

    def record_run_event_trace(self, *, run_id: str, agui_event_trace_json: str) -> None:
        """Persist canonical outbound AG-UI event trace for one run."""

        now = _utcnow()
        with self._session_factory() as session:
            existing_archive_run_id = session.execute(
                select(MessageArchiveRecord.run_id).where(MessageArchiveRecord.run_id == run_id)
            ).scalar_one_or_none()
            if existing_archive_run_id is None:
                archive = MessageArchiveRecord(
                    run_id=run_id,
                    archive_version=1,
                    agui_input_messages_json=None,
                    agui_event_trace_json=agui_event_trace_json,
                    pydantic_all_messages_json=None,
                    pydantic_new_messages_json=None,
                    created_at=now,
                )
                session.add(archive)
            else:
                session.execute(
                    update(MessageArchiveRecord)
                    .where(MessageArchiveRecord.run_id == run_id)
                    .values(agui_event_trace_json=agui_event_trace_json)
                )
            session.commit()

    def record_run_failed(self, *, run_id: str, error_message: str) -> None:
        """Mark run as failed when AG-UI request processing raises."""

        now = _utcnow()
        with self._session_factory() as session:
            existing_run_id = session.execute(
                select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
            ).scalar_one_or_none()
            if existing_run_id is None:
                session.commit()
                return
            session.execute(
                update(AgentRunRecord)
                .where(AgentRunRecord.run_id == run_id)
                .values(status="failed", ended_at=now, error_message=error_message)
            )
            session.commit()

    def load_archived_all_messages_json(self, *, run_id: str) -> str | None:
        """Return persisted full-message archive json for one run."""

        with self._session_factory() as session:
            return session.execute(
                select(MessageArchiveRecord.pydantic_all_messages_json).where(
                    MessageArchiveRecord.run_id == run_id
                )
            ).scalar_one_or_none()

    def list_thread_run_history(
        self,
        *,
        thread_id: str,
        agent_name: str | None = None,
        limit: int = 200,
    ) -> list[ThreadRunHistoryEntry]:
        """Return run/message-archive history rows for one thread ordered by start time."""

        with self._session_factory() as session:
            query = (
                select(
                    AgentRunRecord.run_id,
                    AgentRunRecord.parent_run_id,
                    AgentRunRecord.agent_name,
                    AgentRunRecord.status,
                    AgentRunRecord.user_prompt_text,
                    sa_cast(AgentRunRecord.started_at, Text),
                    sa_cast(AgentRunRecord.ended_at, Text),
                    MessageArchiveRecord.agui_input_messages_json,
                    MessageArchiveRecord.agui_event_trace_json,
                    MessageArchiveRecord.pydantic_all_messages_json,
                    MessageArchiveRecord.pydantic_new_messages_json,
                )
                .outerjoin(
                    MessageArchiveRecord, MessageArchiveRecord.run_id == AgentRunRecord.run_id
                )
                .where(AgentRunRecord.thread_id == thread_id)
            )
            if agent_name is not None:
                query = query.where(AgentRunRecord.agent_name == agent_name)
            rows = session.execute(
                query.order_by(AgentRunRecord.started_at.asc()).limit(limit)
            ).all()
        return [
            ThreadRunHistoryEntry(
                run_id=row.run_id,
                parent_run_id=row.parent_run_id,
                agent_name=row.agent_name,
                status=row.status,
                user_prompt_text=row.user_prompt_text,
                started_at=row.started_at,
                ended_at=row.ended_at,
                agui_input_messages_json=row.agui_input_messages_json,
                agui_event_trace_json=row.agui_event_trace_json,
                pydantic_all_messages_json=row.pydantic_all_messages_json,
                pydantic_new_messages_json=row.pydantic_new_messages_json,
            )
            for row in rows
        ]


@dataclass(frozen=True, slots=True)
class ThreadRunHistoryEntry:
    """One thread-scoped run row with optional message archives."""

    run_id: str
    parent_run_id: str | None
    agent_name: str | None
    status: str
    user_prompt_text: str | None
    started_at: str
    ended_at: str | None
    agui_input_messages_json: str | None
    agui_event_trace_json: str | None
    pydantic_all_messages_json: str | None
    pydantic_new_messages_json: str | None


def extract_last_user_prompt(messages: list[dict[str, Any]]) -> str | None:
    """Extract the most recent user text from AG-UI input messages."""

    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            return text or None
    return None
