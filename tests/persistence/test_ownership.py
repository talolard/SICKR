from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.models import (
    ProjectRecord,
    RoomRecord,
    ThreadRecord,
    UserRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.ownership import (
    DEFAULT_DEV_PROJECT_ID,
    DEFAULT_DEV_ROOM_ID,
    DEFAULT_DEV_USER_ID,
    ensure_default_dev_hierarchy,
    ensure_default_dev_hierarchy_for_session_factory,
    ensure_thread_record,
)


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "ownership_test.sqlite")
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_ensure_default_dev_hierarchy_seeds_expected_rows(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    now = datetime.now(UTC)

    hierarchy = ensure_default_dev_hierarchy_for_session_factory(session_factory)

    assert hierarchy.user_id == DEFAULT_DEV_USER_ID
    assert hierarchy.project_id == DEFAULT_DEV_PROJECT_ID
    assert hierarchy.room_id == DEFAULT_DEV_ROOM_ID

    with session_factory() as session:
        user_row = session.execute(
            select(UserRecord.external_key, UserRecord.display_name).where(
                UserRecord.user_id == DEFAULT_DEV_USER_ID
            )
        ).one()
        project_row = session.execute(
            select(ProjectRecord.user_id, ProjectRecord.title, ProjectRecord.status).where(
                ProjectRecord.project_id == DEFAULT_DEV_PROJECT_ID
            )
        ).one()
        room_row = session.execute(
            select(RoomRecord.project_id, RoomRecord.title, RoomRecord.status).where(
                RoomRecord.room_id == DEFAULT_DEV_ROOM_ID
            )
        ).one()

    assert user_row.external_key == "dev-user"
    assert user_row.display_name == "Tal"
    assert project_row.user_id == DEFAULT_DEV_USER_ID
    assert project_row.title == "Default project"
    assert project_row.status == "active"
    assert room_row.project_id == DEFAULT_DEV_PROJECT_ID
    assert room_row.title == "Untitled room"
    assert room_row.status == "active"

    with session_factory() as session:
        repeated_hierarchy = ensure_default_dev_hierarchy(session, now=now)
        session.commit()

    assert repeated_hierarchy == hierarchy


def test_ensure_thread_record_creates_thread_in_default_room(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    now = datetime.now(UTC)

    with session_factory() as session:
        resolved_room_id = ensure_thread_record(session, thread_id="thread-owned", now=now)
        session.commit()

    assert resolved_room_id == DEFAULT_DEV_ROOM_ID
    with session_factory() as session:
        thread_row = session.execute(
            select(ThreadRecord.room_id, ThreadRecord.status).where(
                ThreadRecord.thread_id == "thread-owned"
            )
        ).one()

    assert thread_row.room_id == DEFAULT_DEV_ROOM_ID
    assert thread_row.status == "active"


def test_ensure_thread_record_rejects_unknown_room_id(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    now = datetime.now(UTC)

    with (
        session_factory() as session,
        pytest.raises(ValueError, match="Unknown room_id `room-missing`"),
    ):
        ensure_thread_record(
            session,
            thread_id="thread-invalid-room",
            now=now,
            room_id="room-missing",
        )


def test_room_titles_are_unique_within_one_project(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    now = datetime.now(UTC)

    with session_factory() as session:
        hierarchy = ensure_default_dev_hierarchy(session, now=now)
        session.add(
            RoomRecord(
                room_id="room-duplicate",
                project_id=hierarchy.project_id,
                title="Untitled room",
                room_type="bedroom",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
