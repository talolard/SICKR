"""Persistence helpers for durable artifact metadata rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import String, cast, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import AgentRunRecord, AssetRecord
from ikea_agent.persistence.ownership import resolve_room_thread_context


@dataclass(frozen=True, slots=True)
class AssetSnapshot:
    """Typed projection of one persisted asset row."""

    asset_id: str
    room_id: str
    thread_id: str
    run_id: str | None
    created_by_tool: str | None
    kind: str
    mime_type: str
    file_name: str | None
    size_bytes: int
    width: int | None
    height: int | None
    created_at: str


class AssetRepository:
    """Repository that links filesystem artifacts to durable DB metadata."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_asset(
        self,
        *,
        asset_id: str,
        room_id: str,
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
            self._ensure_thread(session=session, room_id=room_id, thread_id=thread_id, now=now)
            session.flush()
            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)

            existing_asset_id = session.execute(
                select(AssetRecord.asset_id).where(AssetRecord.asset_id == asset_id)
            ).scalar_one_or_none()
            if existing_asset_id is None:
                session.add(
                    AssetRecord(
                        asset_id=asset_id,
                        room_id=room_id,
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
                        room_id=room_id,
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

    def list_room_images(self, *, room_id: str) -> list[AssetSnapshot]:
        """Return uploaded room images for one room ordered newest-first."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        AssetRecord.asset_id,
                        AssetRecord.room_id,
                        AssetRecord.thread_id,
                        AssetRecord.run_id,
                        AssetRecord.created_by_tool,
                        AssetRecord.kind,
                        AssetRecord.mime_type,
                        AssetRecord.file_name,
                        AssetRecord.size_bytes,
                        AssetRecord.width,
                        AssetRecord.height,
                        cast(AssetRecord.created_at, String).label("created_at"),
                    )
                    .where(AssetRecord.room_id == room_id)
                    .where(AssetRecord.kind == "user_upload")
                    .where(AssetRecord.mime_type.like("image/%"))
                    .order_by(AssetRecord.created_at.desc())
                )
                .mappings()
                .all()
            )
        return [_asset_snapshot_from_row(row) for row in rows]

    def list_assets_by_ids(self, *, room_id: str, asset_ids: list[str]) -> list[AssetSnapshot]:
        """Return persisted asset rows in the input order for one room."""

        if not asset_ids:
            return []
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        AssetRecord.asset_id,
                        AssetRecord.room_id,
                        AssetRecord.thread_id,
                        AssetRecord.run_id,
                        AssetRecord.created_by_tool,
                        AssetRecord.kind,
                        AssetRecord.mime_type,
                        AssetRecord.file_name,
                        AssetRecord.size_bytes,
                        AssetRecord.width,
                        AssetRecord.height,
                        cast(AssetRecord.created_at, String).label("created_at"),
                    )
                    .where(AssetRecord.room_id == room_id)
                    .where(AssetRecord.asset_id.in_(asset_ids))
                )
                .mappings()
                .all()
            )
        snapshots_by_id = {
            snapshot.asset_id: snapshot
            for snapshot in (_asset_snapshot_from_row(row) for row in rows)
        }
        return [snapshots_by_id[asset_id] for asset_id in asset_ids if asset_id in snapshots_by_id]

    @staticmethod
    def _ensure_thread(*, session: Session, room_id: str, thread_id: str, now: datetime) -> None:
        resolve_room_thread_context(
            session,
            room_id=room_id,
            thread_id=thread_id,
            now=now,
        )

    @staticmethod
    def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        return session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()


def _asset_snapshot_from_row(row: RowMapping) -> AssetSnapshot:
    return AssetSnapshot(
        asset_id=str(row["asset_id"]),
        room_id=str(row["room_id"]),
        thread_id=str(row["thread_id"]),
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        created_by_tool=(
            str(row["created_by_tool"]) if row["created_by_tool"] is not None else None
        ),
        kind=str(row["kind"]),
        mime_type=str(row["mime_type"]),
        file_name=str(row["file_name"]) if row["file_name"] is not None else None,
        size_bytes=int(row["size_bytes"]),
        width=int(row["width"]) if row["width"] is not None else None,
        height=int(row["height"]) if row["height"] is not None else None,
        created_at=str(row["created_at"]),
    )
