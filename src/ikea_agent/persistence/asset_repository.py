"""Persistence helpers for durable artifact metadata rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, AssetRecord, ThreadRecord


@dataclass(frozen=True, slots=True)
class PersistedAsset:
    """Durable asset metadata needed to resolve one attachment id."""

    asset_id: str
    thread_id: str
    run_id: str | None
    created_by_tool: str | None
    kind: str
    mime_type: str
    file_name: str | None
    storage_path: str
    sha256: str
    size_bytes: int
    width: int | None
    height: int | None


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

    def get_asset(self, *, asset_id: str) -> PersistedAsset | None:
        """Return one persisted asset row for attachment-resolution flows."""

        with self._session_factory() as session:
            row = session.execute(
                select(
                    AssetRecord.asset_id,
                    AssetRecord.thread_id,
                    AssetRecord.run_id,
                    AssetRecord.created_by_tool,
                    AssetRecord.kind,
                    AssetRecord.mime_type,
                    AssetRecord.file_name,
                    AssetRecord.storage_path,
                    AssetRecord.sha256,
                    AssetRecord.size_bytes,
                    AssetRecord.width,
                    AssetRecord.height,
                ).where(AssetRecord.asset_id == asset_id)
            ).one_or_none()
        if row is None:
            return None
        return PersistedAsset(
            asset_id=str(row.asset_id),
            thread_id=str(row.thread_id),
            run_id=str(row.run_id) if row.run_id is not None else None,
            created_by_tool=str(row.created_by_tool) if row.created_by_tool is not None else None,
            kind=str(row.kind),
            mime_type=str(row.mime_type),
            file_name=str(row.file_name) if row.file_name is not None else None,
            storage_path=str(row.storage_path),
            sha256=str(row.sha256),
            size_bytes=int(row.size_bytes),
            width=int(row.width) if row.width is not None else None,
            height=int(row.height) if row.height is not None else None,
        )

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
