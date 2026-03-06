"""Persistence helpers for AG-UI run lifecycle and message archives."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
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
