"""Shared session-scoped helpers for persistence repositories."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ikea_agent.persistence.models import AgentRunRecord, RoomRecord, ThreadRecord


def lock_room_row(session: Session, *, room_id: str) -> None:
    """Acquire the room row lock used to serialize room-scoped revision writes."""

    session.execute(
        select(RoomRecord.room_id).where(RoomRecord.room_id == room_id).with_for_update()
    ).scalar_one()


def lock_thread_row(session: Session, *, thread_id: str) -> None:
    """Acquire the thread row lock used to serialize thread-scoped transcript writes."""

    session.execute(
        select(ThreadRecord.thread_id).where(ThreadRecord.thread_id == thread_id).with_for_update()
    ).scalar_one()


def resolve_existing_run_id(session: Session, *, run_id: str | None) -> str | None:
    """Return one persisted run id or `None` when the reference does not exist."""

    if run_id is None:
        return None
    return session.execute(
        select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
    ).scalar_one_or_none()


def touch_thread_activity(
    session: Session,
    *,
    thread_id: str,
    now: datetime,
) -> None:
    """Refresh the durable activity timestamps for one thread row."""

    session.execute(
        update(ThreadRecord)
        .where(ThreadRecord.thread_id == thread_id)
        .values(updated_at=now, last_activity_at=now)
    )
