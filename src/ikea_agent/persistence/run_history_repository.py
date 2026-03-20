"""Persistence helpers for AG-UI run lifecycle state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord
from ikea_agent.persistence.ownership import resolve_room_thread_context


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RunHistoryRepository:
    """Repository for persisting thread and run lifecycle state."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_run_start(
        self,
        *,
        room_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str | None,
        parent_run_id: str | None,
        user_prompt_text: str | None,
    ) -> None:
        """Create/update thread and run rows at AG-UI request start."""

        now = _utcnow()
        with self._session_factory() as session:
            resolve_room_thread_context(
                session,
                room_id=room_id,
                thread_id=thread_id,
                now=now,
            )
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

            session.commit()

    def record_run_complete(self, *, run_id: str) -> None:
        """Mark one run as completed."""

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
