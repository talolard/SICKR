"""Persistence helpers for room- and project-scoped durable facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast as typing_cast
from uuid import uuid4

from sqlalchemy import String, cast, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    ProjectFactRecord,
    RoomFactRecord,
    RoomRecord,
    ThreadRecord,
)
from ikea_agent.persistence.ownership import require_room_record
from ikea_agent.persistence.repository_helpers import resolve_existing_run_id
from ikea_agent.shared.types import (
    KnownFactKind,
    KnownFactMemory,
    KnownFactMemoryInput,
    RoomIdentity,
    RoomType,
)


def _parse_known_fact_kind(raw_kind: str) -> KnownFactKind:
    """Validate persisted fact kinds before hydrating typed models."""

    if raw_kind in ("constraint", "fact", "preference"):
        return raw_kind
    raise ValueError(f"Unknown known fact kind: {raw_kind}")


@dataclass(frozen=True, slots=True)
class RoomContextSnapshot:
    """Durable room identity plus current room/project fact context."""

    room_identity: RoomIdentity
    room_facts: list[KnownFactMemory]
    project_facts: list[KnownFactMemory]


class ContextFactRepository:
    """Persist and reload durable room/project facts plus room identity."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load_room_context(self, *, room_id: str) -> RoomContextSnapshot:
        """Return the durable room identity plus all room/project facts."""

        with self._session_factory() as session:
            room_identity = _load_room_identity(session, room_id=room_id)
            return RoomContextSnapshot(
                room_identity=room_identity,
                room_facts=_list_room_facts(session, room_id=room_id),
                project_facts=_list_project_facts(session, project_id=room_identity.project_id),
            )

    def list_known_facts_for_thread(self, *, thread_id: str) -> list[KnownFactMemory]:
        """Return room and project facts visible from one thread."""

        with self._session_factory() as session:
            room_identity = _load_room_identity_for_thread(session, thread_id=thread_id)
            room_facts = _list_room_facts(session, room_id=room_identity.room_id)
            project_facts = _list_project_facts(session, project_id=room_identity.project_id)
        return sorted(
            [*room_facts, *project_facts],
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def upsert_room_facts(
        self,
        *,
        room_id: str,
        run_id: str | None,
        facts: list[KnownFactMemoryInput],
    ) -> list[KnownFactMemory]:
        """Insert or refresh one or more normalized room facts."""

        return self._upsert_facts(
            room_id=room_id,
            run_id=run_id,
            facts=facts,
            scope="room",
        )

    def upsert_project_facts(
        self,
        *,
        project_id: str,
        run_id: str | None,
        facts: list[KnownFactMemoryInput],
    ) -> list[KnownFactMemory]:
        """Insert or refresh one or more normalized project facts."""

        return self._upsert_facts(
            project_id=project_id,
            run_id=run_id,
            facts=facts,
            scope="project",
        )

    def rename_room(self, *, room_id: str, title: str) -> RoomIdentity:
        """Persist one durable room title change and return the updated identity."""

        now = datetime.now(UTC)
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Room title must not be empty.")

        with self._session_factory() as session:
            room_identity = _load_room_identity(session, room_id=room_id)
            try:
                session.execute(
                    update(RoomRecord)
                    .where(RoomRecord.room_id == room_id)
                    .values(title=normalized_title, updated_at=now)
                )
                session.commit()
            except IntegrityError as exc:
                raise ValueError("Room title must be unique within one project.") from exc
        return room_identity.model_copy(update={"title": normalized_title})

    def set_room_type(self, *, room_id: str, room_type: RoomType) -> RoomIdentity:
        """Persist one durable room type change and return the updated identity."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            room_identity = _load_room_identity(session, room_id=room_id)
            session.execute(
                update(RoomRecord)
                .where(RoomRecord.room_id == room_id)
                .values(room_type=room_type, updated_at=now)
            )
            session.commit()
        return room_identity.model_copy(update={"room_type": room_type})

    def _upsert_facts(
        self,
        *,
        run_id: str | None,
        facts: list[KnownFactMemoryInput],
        scope: str,
        room_id: str | None = None,
        project_id: str | None = None,
    ) -> list[KnownFactMemory]:
        if not facts:
            return self._list_existing_facts(
                scope=scope,
                room_id=room_id,
                project_id=project_id,
            )

        now = datetime.now(UTC)
        with self._session_factory() as session:
            persisted_run_id = resolve_existing_run_id(session, run_id=run_id)
            if scope == "room":
                return self._upsert_room_facts_with_session(
                    session=session,
                    room_id=room_id,
                    run_id=persisted_run_id,
                    facts=facts,
                    now=now,
                )

            return self._upsert_project_facts_with_session(
                session=session,
                project_id=project_id,
                run_id=persisted_run_id,
                facts=facts,
                now=now,
            )

    def _list_existing_facts(
        self,
        *,
        scope: str,
        room_id: str | None,
        project_id: str | None,
    ) -> list[KnownFactMemory]:
        if scope == "room":
            if room_id is None:
                raise ValueError("Room facts require a room_id.")
            return self.load_room_context(room_id=room_id).room_facts
        if project_id is None:
            raise ValueError("Project facts require a project_id.")
        return self._list_project_facts(project_id=project_id)

    def _upsert_room_facts_with_session(
        self,
        *,
        session: Session,
        room_id: str | None,
        run_id: str | None,
        facts: list[KnownFactMemoryInput],
        now: datetime,
    ) -> list[KnownFactMemory]:
        if room_id is None:
            raise ValueError("Room facts require a room_id.")
        room_identity = _load_room_identity(session, room_id=room_id)
        for fact in facts:
            _upsert_room_fact_row(
                session,
                room_id=room_identity.room_id,
                run_id=run_id,
                fact=fact,
                now=now,
            )
        session.commit()
        return _list_room_facts(session, room_id=room_identity.room_id)

    def _upsert_project_facts_with_session(
        self,
        *,
        session: Session,
        project_id: str | None,
        run_id: str | None,
        facts: list[KnownFactMemoryInput],
        now: datetime,
    ) -> list[KnownFactMemory]:
        if project_id is None:
            raise ValueError("Project facts require a project_id.")
        for fact in facts:
            _upsert_project_fact_row(
                session,
                project_id=project_id,
                run_id=run_id,
                fact=fact,
                now=now,
            )
        session.commit()
        return _list_project_facts(session, project_id=project_id)

    def _list_project_facts(self, *, project_id: str) -> list[KnownFactMemory]:
        with self._session_factory() as session:
            return _list_project_facts(session, project_id=project_id)


def _load_room_identity(session: Session, *, room_id: str) -> RoomIdentity:
    require_room_record(session, room_id=room_id)
    row = session.execute(
        select(
            RoomRecord.room_id,
            RoomRecord.project_id,
            RoomRecord.title,
            RoomRecord.room_type,
        ).where(RoomRecord.room_id == room_id)
    ).one()
    return RoomIdentity(
        room_id=str(row.room_id),
        project_id=str(row.project_id),
        title=str(row.title),
        room_type=typing_cast("RoomType | None", row.room_type),
    )


def _load_room_identity_for_thread(session: Session, *, thread_id: str) -> RoomIdentity:
    room_id = session.execute(
        select(ThreadRecord.room_id).where(ThreadRecord.thread_id == thread_id)
    ).scalar_one_or_none()
    if room_id is None:
        raise ValueError(f"Unknown thread_id `{thread_id}`.")
    return _load_room_identity(session, room_id=str(room_id))


def _upsert_room_fact_row(
    session: Session,
    *,
    room_id: str,
    run_id: str | None,
    fact: KnownFactMemoryInput,
    now: datetime,
) -> None:
    existing = session.execute(
        select(RoomFactRecord.room_fact_id)
        .where(RoomFactRecord.room_id == room_id)
        .where(RoomFactRecord.signal_key == fact.signal_key)
        .where(RoomFactRecord.value == fact.value)
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            RoomFactRecord(
                room_fact_id=f"rfact-{uuid4().hex[:20]}",
                room_id=room_id,
                run_id=run_id,
                signal_key=fact.signal_key,
                kind=fact.kind,
                value=fact.value,
                summary=fact.summary,
                source_message_text=fact.source_message_text,
                created_at=now,
                updated_at=now,
            )
        )
        return
    session.execute(
        update(RoomFactRecord)
        .where(RoomFactRecord.room_fact_id == existing)
        .values(
            run_id=run_id,
            kind=fact.kind,
            summary=fact.summary,
            source_message_text=fact.source_message_text,
            updated_at=now,
        )
    )


def _upsert_project_fact_row(
    session: Session,
    *,
    project_id: str,
    run_id: str | None,
    fact: KnownFactMemoryInput,
    now: datetime,
) -> None:
    existing = session.execute(
        select(ProjectFactRecord.project_fact_id)
        .where(ProjectFactRecord.project_id == project_id)
        .where(ProjectFactRecord.signal_key == fact.signal_key)
        .where(ProjectFactRecord.value == fact.value)
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            ProjectFactRecord(
                project_fact_id=f"pfact-{uuid4().hex[:20]}",
                project_id=project_id,
                run_id=run_id,
                signal_key=fact.signal_key,
                kind=fact.kind,
                value=fact.value,
                summary=fact.summary,
                source_message_text=fact.source_message_text,
                created_at=now,
                updated_at=now,
            )
        )
        return
    session.execute(
        update(ProjectFactRecord)
        .where(ProjectFactRecord.project_fact_id == existing)
        .values(
            run_id=run_id,
            kind=fact.kind,
            summary=fact.summary,
            source_message_text=fact.source_message_text,
            updated_at=now,
        )
    )


def _list_room_facts(session: Session, *, room_id: str) -> list[KnownFactMemory]:
    rows = session.execute(
        select(
            RoomFactRecord.room_fact_id,
            RoomFactRecord.signal_key,
            RoomFactRecord.kind,
            RoomFactRecord.value,
            RoomFactRecord.summary,
            RoomFactRecord.source_message_text,
            cast(RoomFactRecord.created_at, String),
            cast(RoomFactRecord.updated_at, String),
            RoomFactRecord.run_id,
        )
        .where(RoomFactRecord.room_id == room_id)
        .order_by(RoomFactRecord.updated_at.desc())
    ).all()
    return [
        KnownFactMemory(
            fact_id=str(row.room_fact_id),
            scope="room",
            signal_key=str(row.signal_key),
            kind=_parse_known_fact_kind(str(row.kind)),
            value=str(row.value),
            summary=str(row.summary),
            source_message_text=str(row.source_message_text),
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
            run_id=str(row.run_id) if row.run_id is not None else None,
        )
        for row in rows
    ]


def _list_project_facts(session: Session, *, project_id: str) -> list[KnownFactMemory]:
    rows = session.execute(
        select(
            ProjectFactRecord.project_fact_id,
            ProjectFactRecord.signal_key,
            ProjectFactRecord.kind,
            ProjectFactRecord.value,
            ProjectFactRecord.summary,
            ProjectFactRecord.source_message_text,
            cast(ProjectFactRecord.created_at, String),
            cast(ProjectFactRecord.updated_at, String),
            ProjectFactRecord.run_id,
        )
        .where(ProjectFactRecord.project_id == project_id)
        .order_by(ProjectFactRecord.updated_at.desc())
    ).all()
    return [
        KnownFactMemory(
            fact_id=str(row.project_fact_id),
            scope="project",
            signal_key=str(row.signal_key),
            kind=_parse_known_fact_kind(str(row.kind)),
            value=str(row.value),
            summary=str(row.summary),
            source_message_text=str(row.source_message_text),
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
            run_id=str(row.run_id) if row.run_id is not None else None,
        )
        for row in rows
    ]
