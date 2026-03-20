"""Helpers for the default dev ownership hierarchy and thread bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import ProjectRecord, RoomRecord, ThreadRecord, UserRecord

DEFAULT_DEV_USER_ID = "user-dev-default"
DEFAULT_DEV_PROJECT_ID = "project-dev-default"
DEFAULT_DEV_ROOM_ID = "room-dev-default"


@dataclass(frozen=True, slots=True)
class DefaultDevHierarchy:
    """Stable ids for the default seeded dev hierarchy."""

    user_id: str
    project_id: str
    room_id: str


def ensure_default_dev_hierarchy(
    session: Session,
    *,
    now: datetime,
) -> DefaultDevHierarchy:
    """Seed the default dev user, project, and room rows when missing."""

    if session.get(UserRecord, DEFAULT_DEV_USER_ID) is None:
        session.add(
            UserRecord(
                user_id=DEFAULT_DEV_USER_ID,
                external_key="dev-user",
                display_name="Tal",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()

    if session.get(ProjectRecord, DEFAULT_DEV_PROJECT_ID) is None:
        session.add(
            ProjectRecord(
                project_id=DEFAULT_DEV_PROJECT_ID,
                user_id=DEFAULT_DEV_USER_ID,
                title="Default project",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()

    if session.get(RoomRecord, DEFAULT_DEV_ROOM_ID) is None:
        session.add(
            RoomRecord(
                room_id=DEFAULT_DEV_ROOM_ID,
                project_id=DEFAULT_DEV_PROJECT_ID,
                title="Untitled room",
                room_type=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()

    return DefaultDevHierarchy(
        user_id=DEFAULT_DEV_USER_ID,
        project_id=DEFAULT_DEV_PROJECT_ID,
        room_id=DEFAULT_DEV_ROOM_ID,
    )


def ensure_default_dev_hierarchy_for_session_factory(
    session_factory: sessionmaker[Session],
) -> DefaultDevHierarchy:
    """Seed the default dev hierarchy through the shared session factory."""

    now = datetime.now(UTC)
    with session_factory() as session:
        hierarchy = ensure_default_dev_hierarchy(session, now=now)
        session.commit()
        return hierarchy


def require_room_record(session: Session, *, room_id: str) -> None:
    """Fail when one room id does not exist."""

    if session.get(RoomRecord, room_id) is None:
        raise ValueError(f"Unknown room_id `{room_id}`.")


def ensure_thread_record(
    session: Session,
    *,
    thread_id: str,
    now: datetime,
    room_id: str | None = None,
    title: str | None = None,
) -> str:
    """Ensure one thread row exists and belongs to a valid room."""

    existing_room_id = session.execute(
        select(ThreadRecord.room_id).where(ThreadRecord.thread_id == thread_id)
    ).scalar_one_or_none()
    if existing_room_id is not None:
        if room_id is not None and str(existing_room_id) != room_id:
            raise ValueError(
                f"Thread `{thread_id}` belongs to room `{existing_room_id}`, not `{room_id}`."
            )
        return str(existing_room_id)

    resolved_room_id = room_id or ensure_default_dev_hierarchy(session, now=now).room_id
    session.flush()
    room_exists = session.execute(
        select(RoomRecord.room_id).where(RoomRecord.room_id == resolved_room_id)
    ).scalar_one_or_none()
    if room_exists is None:
        raise ValueError(f"Unknown room_id `{resolved_room_id}` for thread `{thread_id}`.")

    session.add(
        ThreadRecord(
            thread_id=thread_id,
            room_id=resolved_room_id,
            title=title,
            status="active",
            created_at=now,
            updated_at=now,
            last_activity_at=now,
        )
    )
    return resolved_room_id


def resolve_room_thread_context(
    session: Session,
    *,
    room_id: str,
    thread_id: str,
    now: datetime,
    title: str | None = None,
) -> tuple[str, str]:
    """Resolve one explicit room/thread pair and create the thread only within that room."""

    if room_id == DEFAULT_DEV_ROOM_ID:
        ensure_default_dev_hierarchy(session, now=now)
    require_room_record(session, room_id=room_id)
    existing_room_id = session.execute(
        select(ThreadRecord.room_id).where(ThreadRecord.thread_id == thread_id)
    ).scalar_one_or_none()
    if existing_room_id is None:
        ensure_thread_record(
            session,
            thread_id=thread_id,
            room_id=room_id,
            now=now,
            title=title,
        )
        return room_id, thread_id

    resolved_room_id = str(existing_room_id)
    if resolved_room_id != room_id:
        raise ValueError(
            f"Thread `{thread_id}` belongs to room `{resolved_room_id}`, not `{room_id}`."
        )
    return resolved_room_id, thread_id


def resolve_room_thread_context_for_session_factory(
    session_factory: sessionmaker[Session],
    *,
    room_id: str,
    thread_id: str,
    now: datetime,
    title: str | None = None,
) -> tuple[str, str]:
    """Resolve one explicit room/thread pair through the shared session factory."""

    with session_factory() as session:
        resolved = resolve_room_thread_context(
            session,
            room_id=room_id,
            thread_id=thread_id,
            now=now,
            title=title,
        )
        session.commit()
        return resolved
