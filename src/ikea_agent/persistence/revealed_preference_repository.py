"""Persistence helpers for thread-scoped revealed preference memory."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import String, cast, select, update
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, RevealedPreferenceRecord
from ikea_agent.persistence.ownership import ensure_thread_record
from ikea_agent.shared.types import (
    RevealedPreferenceKind,
    RevealedPreferenceMemory,
    RevealedPreferenceMemoryInput,
)


def _parse_preference_kind(raw_kind: str) -> RevealedPreferenceKind:
    """Validate persisted preference kinds before hydrating typed models."""

    if raw_kind in ("constraint", "fact", "preference"):
        return raw_kind
    raise ValueError(f"Unknown revealed preference kind: {raw_kind}")


class RevealedPreferenceRepository:
    """Persist and reload normalized thread-scoped preference memory."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_preferences(
        self,
        *,
        thread_id: str,
        run_id: str | None,
        preferences: list[RevealedPreferenceMemoryInput],
    ) -> list[RevealedPreferenceMemory]:
        """Insert or refresh one or more normalized preference items for a thread."""

        if not preferences:
            return self.list_preferences(thread_id=thread_id)

        now = datetime.now(UTC)
        with self._session_factory() as session:
            self._ensure_thread(session=session, thread_id=thread_id, now=now)
            session.flush()
            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)
            for preference in preferences:
                existing = session.execute(
                    select(
                        RevealedPreferenceRecord.revealed_preference_id,
                    )
                    .where(RevealedPreferenceRecord.thread_id == thread_id)
                    .where(RevealedPreferenceRecord.signal_key == preference.signal_key)
                    .where(RevealedPreferenceRecord.value == preference.value)
                ).one_or_none()
                if existing is None:
                    session.add(
                        RevealedPreferenceRecord(
                            revealed_preference_id=f"rmem-{uuid4().hex[:20]}",
                            thread_id=thread_id,
                            run_id=persisted_run_id,
                            signal_key=preference.signal_key,
                            kind=preference.kind,
                            value=preference.value,
                            summary=preference.summary,
                            source_message_text=preference.source_message_text,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    continue
                session.execute(
                    update(RevealedPreferenceRecord)
                    .where(
                        RevealedPreferenceRecord.revealed_preference_id
                        == existing.revealed_preference_id
                    )
                    .values(
                        run_id=persisted_run_id,
                        kind=preference.kind,
                        summary=preference.summary,
                        source_message_text=preference.source_message_text,
                        updated_at=now,
                    )
                )
            session.commit()

        return self.list_preferences(thread_id=thread_id)

    def list_preferences(self, *, thread_id: str) -> list[RevealedPreferenceMemory]:
        """Return persisted thread memory ordered by most recent update first."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    RevealedPreferenceRecord.revealed_preference_id,
                    RevealedPreferenceRecord.signal_key,
                    RevealedPreferenceRecord.kind,
                    RevealedPreferenceRecord.value,
                    RevealedPreferenceRecord.summary,
                    RevealedPreferenceRecord.source_message_text,
                    cast(RevealedPreferenceRecord.created_at, String),
                    cast(RevealedPreferenceRecord.updated_at, String),
                    RevealedPreferenceRecord.run_id,
                )
                .where(RevealedPreferenceRecord.thread_id == thread_id)
                .order_by(RevealedPreferenceRecord.updated_at.desc())
            ).all()
        return [
            RevealedPreferenceMemory(
                memory_id=str(row.revealed_preference_id),
                signal_key=str(row.signal_key),
                kind=_parse_preference_kind(str(row.kind)),
                value=str(row.value),
                summary=str(row.summary),
                source_message_text=str(row.source_message_text),
                created_at=str(row.created_at),
                updated_at=str(row.updated_at),
                run_id=str(row.run_id) if row.run_id is not None else None,
            )
            for row in rows
        ]

    @staticmethod
    def _ensure_thread(*, session: Session, thread_id: str, now: datetime) -> None:
        ensure_thread_record(session, thread_id=thread_id, now=now)

    @staticmethod
    def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        return session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()
