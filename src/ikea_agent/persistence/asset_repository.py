"""Persistence helpers for durable artifact metadata rows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, AssetRecord, ThreadRecord


class AssetRepository:
    """Repository that links filesystem artifacts to durable DB metadata."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_asset(
        self,
        *,
        asset_id: str,
        thread_id: str,
        run_id: str | None,
        created_by_tool: str | None,
        kind: str,
        mime_type: str,
        file_name: str | None,
        storage_path: str,
        sha256: str,
        size_bytes: int,
        width: int | None,
        height: int | None,
    ) -> None:
        """Insert or update one asset row and ensure FK parents exist."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            self._ensure_thread(session=session, thread_id=thread_id, now=now)
            session.flush()
            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)

            existing_asset_id = session.execute(
                select(AssetRecord.asset_id).where(AssetRecord.asset_id == asset_id)
            ).scalar_one_or_none()
            if existing_asset_id is None:
                session.add(
                    AssetRecord(
                        asset_id=asset_id,
                        thread_id=thread_id,
                        run_id=persisted_run_id,
                        created_by_tool=created_by_tool,
                        kind=kind,
                        mime_type=mime_type,
                        file_name=file_name,
                        storage_path=storage_path,
                        sha256=sha256,
                        size_bytes=size_bytes,
                        width=width,
                        height=height,
                        created_at=now,
                    )
                )
            else:
                session.execute(
                    update(AssetRecord)
                    .where(AssetRecord.asset_id == asset_id)
                    .values(
                        thread_id=thread_id,
                        run_id=persisted_run_id,
                        created_by_tool=created_by_tool,
                        kind=kind,
                        mime_type=mime_type,
                        file_name=file_name,
                        storage_path=storage_path,
                        sha256=sha256,
                        size_bytes=size_bytes,
                        width=width,
                        height=height,
                    )
                )

            session.commit()

    @staticmethod
    def _ensure_thread(*, session: Session, thread_id: str, now: datetime) -> None:
        existing_thread_id = session.execute(
            select(ThreadRecord.thread_id).where(ThreadRecord.thread_id == thread_id)
        ).scalar_one_or_none()
        if existing_thread_id is None:
            session.add(
                ThreadRecord(
                    thread_id=thread_id,
                    owner_id=None,
                    title=None,
                    status="active",
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                )
            )

    @staticmethod
    def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        return session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()
