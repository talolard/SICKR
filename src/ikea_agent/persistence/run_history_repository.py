"""Persistence helpers for AG-UI run lifecycle state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, ThreadMessageSegmentRecord
from ikea_agent.persistence.ownership import resolve_room_thread_context


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RunHistoryRepository:
    """Repository for canonical thread transcript and run lifecycle state."""

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

    def record_run_complete(
        self,
        *,
        run_id: str,
        new_messages_json: bytes | None = None,
    ) -> None:
        """Mark one run as completed."""

        now = _utcnow()
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                session.commit()
                return
            self._upsert_thread_message_segment(
                session,
                run_id=run_id,
                thread_id=run.thread_id,
                new_messages_json=new_messages_json,
                now=now,
            )
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

    def load_message_history(self, *, thread_id: str) -> list[ModelMessage]:
        """Load the canonical ordered PydanticAI history for one thread."""

        with self._session_factory() as session:
            encoded_segments = session.execute(
                select(ThreadMessageSegmentRecord.messages_json)
                .where(ThreadMessageSegmentRecord.thread_id == thread_id)
                .order_by(ThreadMessageSegmentRecord.sequence_no)
            ).scalars()
            history: list[ModelMessage] = []
            for encoded_segment in encoded_segments:
                history.extend(self._decode_messages_json(encoded_segment))
            return history

    def _upsert_thread_message_segment(
        self,
        session: Session,
        *,
        run_id: str,
        thread_id: str,
        new_messages_json: bytes | None,
        now: datetime,
    ) -> None:
        if new_messages_json is None:
            return

        messages = self._decode_messages_json(new_messages_json)
        if not messages:
            return

        serialized_messages = new_messages_json.decode("utf-8")
        existing_segment = session.execute(
            select(
                ThreadMessageSegmentRecord.thread_message_segment_id,
                ThreadMessageSegmentRecord.sequence_no,
            ).where(ThreadMessageSegmentRecord.run_id == run_id)
        ).one_or_none()
        if existing_segment is None:
            next_sequence = self._next_thread_sequence(session, thread_id=thread_id)
            session.add(
                ThreadMessageSegmentRecord(
                    thread_message_segment_id=f"msgseg-{uuid4().hex[:20]}",
                    thread_id=thread_id,
                    run_id=run_id,
                    sequence_no=next_sequence,
                    messages_json=serialized_messages,
                    created_at=now,
                )
            )
            return

        session.execute(
            update(ThreadMessageSegmentRecord)
            .where(
                ThreadMessageSegmentRecord.thread_message_segment_id
                == existing_segment.thread_message_segment_id
            )
            .values(messages_json=serialized_messages)
        )

    def _next_thread_sequence(self, session: Session, *, thread_id: str) -> int:
        current_max = session.execute(
            select(func.max(ThreadMessageSegmentRecord.sequence_no)).where(
                ThreadMessageSegmentRecord.thread_id == thread_id
            )
        ).scalar_one_or_none()
        return int(current_max or 0) + 1

    def _decode_messages_json(self, messages_json: bytes | str) -> list[ModelMessage]:
        decoded_messages = ModelMessagesTypeAdapter.validate_json(messages_json)
        return list(decoded_messages)


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
