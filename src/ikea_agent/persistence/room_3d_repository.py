"""Persistence helpers for room 3D assets and camera snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import String, cast, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    AssetRecord,
    Room3DAssetRecord,
    Room3DSnapshotRecord,
)
from ikea_agent.persistence.ownership import require_thread_record
from ikea_agent.persistence.repository_helpers import (
    resolve_existing_run_id,
    touch_thread_activity,
)


@dataclass(frozen=True, slots=True)
class Room3DAssetEntry:
    """One persisted room 3D asset binding."""

    room_3d_asset_id: str
    room_id: str
    thread_id: str
    run_id: str | None
    source_asset_id: str
    usd_format: str
    metadata: dict[str, object]
    created_at: str


@dataclass(frozen=True, slots=True)
class Room3DSnapshotEntry:
    """One persisted room 3D snapshot metadata row."""

    room_3d_snapshot_id: str
    room_id: str
    thread_id: str
    run_id: str | None
    snapshot_asset_id: str
    room_3d_asset_id: str | None
    camera: dict[str, object]
    lighting: dict[str, object]
    comment: str | None
    created_at: str


class Room3DRepository:
    """Create and query room 3D persistence records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_room_3d_asset(
        self,
        *,
        room_id: str,
        thread_id: str,
        source_asset_id: str,
        usd_format: str,
        metadata: dict[str, object],
        run_id: str | None,
    ) -> Room3DAssetEntry:
        """Insert one room 3D asset row and return the stored entry."""

        now = datetime.now(UTC)
        room_3d_asset_id = f"room3d-asset-{uuid4().hex[:16]}"

        with self._session_factory() as session:
            require_thread_record(session, room_id=room_id, thread_id=thread_id)
            if not self._asset_exists_in_room(
                session=session,
                room_id=room_id,
                asset_id=source_asset_id,
            ):
                raise ValueError(f"Unknown source asset `{source_asset_id}` for room `{room_id}`.")
            persisted_run_id = resolve_existing_run_id(session, run_id=run_id)
            session.add(
                Room3DAssetRecord(
                    room_3d_asset_id=room_3d_asset_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    source_asset_id=source_asset_id,
                    usd_format=usd_format,
                    metadata_json=json.dumps(metadata),
                    created_at=now,
                )
            )
            touch_thread_activity(session, thread_id=thread_id, now=now)
            session.commit()

        stored = self.get_room_3d_asset(room_3d_asset_id=room_3d_asset_id)
        if stored is None:  # pragma: no cover - defensive guard
            raise ValueError("Stored room_3d_asset row was not found after insert.")
        return stored

    def list_room_3d_assets(self, *, room_id: str) -> list[Room3DAssetEntry]:
        """Return all room 3D assets for one room."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        Room3DAssetRecord.room_3d_asset_id,
                        Room3DAssetRecord.room_id,
                        Room3DAssetRecord.thread_id,
                        Room3DAssetRecord.run_id,
                        Room3DAssetRecord.source_asset_id,
                        Room3DAssetRecord.usd_format,
                        Room3DAssetRecord.metadata_json,
                        cast(Room3DAssetRecord.created_at, String),
                    )
                    .where(Room3DAssetRecord.room_id == room_id)
                    .order_by(Room3DAssetRecord.created_at.desc())
                )
                .mappings()
                .all()
            )
        return [_asset_from_row(row) for row in rows]

    def get_room_3d_asset(self, *, room_3d_asset_id: str) -> Room3DAssetEntry | None:
        """Fetch one room 3D asset by id."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    select(
                        Room3DAssetRecord.room_3d_asset_id,
                        Room3DAssetRecord.room_id,
                        Room3DAssetRecord.thread_id,
                        Room3DAssetRecord.run_id,
                        Room3DAssetRecord.source_asset_id,
                        Room3DAssetRecord.usd_format,
                        Room3DAssetRecord.metadata_json,
                        cast(Room3DAssetRecord.created_at, String),
                    ).where(Room3DAssetRecord.room_3d_asset_id == room_3d_asset_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _asset_from_row(row)

    def create_room_3d_snapshot(
        self,
        *,
        room_id: str,
        thread_id: str,
        snapshot_asset_id: str,
        camera: dict[str, object],
        lighting: dict[str, object],
        comment: str | None,
        room_3d_asset_id: str | None,
        run_id: str | None,
    ) -> Room3DSnapshotEntry:
        """Insert one room 3D snapshot row and return the stored entry."""

        now = datetime.now(UTC)
        room_3d_snapshot_id = f"room3d-snapshot-{uuid4().hex[:16]}"

        with self._session_factory() as session:
            require_thread_record(session, room_id=room_id, thread_id=thread_id)
            if not self._asset_exists_in_room(
                session=session,
                room_id=room_id,
                asset_id=snapshot_asset_id,
            ):
                raise ValueError(
                    f"Unknown snapshot asset `{snapshot_asset_id}` for room `{room_id}`."
                )
            if room_3d_asset_id is not None and not self._room_3d_asset_exists_in_room(
                session=session,
                room_id=room_id,
                room_3d_asset_id=room_3d_asset_id,
            ):
                raise ValueError(
                    f"Unknown room_3d_asset_id `{room_3d_asset_id}` for room `{room_id}`."
                )
            persisted_run_id = resolve_existing_run_id(session, run_id=run_id)
            session.add(
                Room3DSnapshotRecord(
                    room_3d_snapshot_id=room_3d_snapshot_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    snapshot_asset_id=snapshot_asset_id,
                    room_3d_asset_id=room_3d_asset_id,
                    camera_json=json.dumps(camera),
                    lighting_json=json.dumps(lighting),
                    comment=comment,
                    created_at=now,
                )
            )
            touch_thread_activity(session, thread_id=thread_id, now=now)
            session.commit()

        stored = self.get_room_3d_snapshot(room_3d_snapshot_id=room_3d_snapshot_id)
        if stored is None:  # pragma: no cover - defensive guard
            raise ValueError("Stored room_3d_snapshot row was not found after insert.")
        return stored

    def list_room_3d_snapshots(self, *, room_id: str) -> list[Room3DSnapshotEntry]:
        """Return all room 3D snapshots for one room."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        Room3DSnapshotRecord.room_3d_snapshot_id,
                        Room3DSnapshotRecord.room_id,
                        Room3DSnapshotRecord.thread_id,
                        Room3DSnapshotRecord.run_id,
                        Room3DSnapshotRecord.snapshot_asset_id,
                        Room3DSnapshotRecord.room_3d_asset_id,
                        Room3DSnapshotRecord.camera_json,
                        Room3DSnapshotRecord.lighting_json,
                        Room3DSnapshotRecord.comment,
                        cast(Room3DSnapshotRecord.created_at, String),
                    )
                    .where(Room3DSnapshotRecord.room_id == room_id)
                    .order_by(Room3DSnapshotRecord.created_at.desc())
                )
                .mappings()
                .all()
            )
        return [_snapshot_from_row(row) for row in rows]

    def get_room_3d_snapshot(self, *, room_3d_snapshot_id: str) -> Room3DSnapshotEntry | None:
        """Fetch one room 3D snapshot by id."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    select(
                        Room3DSnapshotRecord.room_3d_snapshot_id,
                        Room3DSnapshotRecord.room_id,
                        Room3DSnapshotRecord.thread_id,
                        Room3DSnapshotRecord.run_id,
                        Room3DSnapshotRecord.snapshot_asset_id,
                        Room3DSnapshotRecord.room_3d_asset_id,
                        Room3DSnapshotRecord.camera_json,
                        Room3DSnapshotRecord.lighting_json,
                        Room3DSnapshotRecord.comment,
                        cast(Room3DSnapshotRecord.created_at, String),
                    ).where(Room3DSnapshotRecord.room_3d_snapshot_id == room_3d_snapshot_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _snapshot_from_row(row)

    @staticmethod
    def _asset_exists_in_room(*, session: Session, room_id: str, asset_id: str) -> bool:
        return (
            session.execute(
                select(AssetRecord.asset_id)
                .where(AssetRecord.asset_id == asset_id)
                .where(AssetRecord.room_id == room_id)
            ).scalar_one_or_none()
            is not None
        )

    @staticmethod
    def _room_3d_asset_exists_in_room(
        *,
        session: Session,
        room_id: str,
        room_3d_asset_id: str,
    ) -> bool:
        return (
            session.execute(
                select(Room3DAssetRecord.room_3d_asset_id)
                .where(Room3DAssetRecord.room_3d_asset_id == room_3d_asset_id)
                .where(Room3DAssetRecord.room_id == room_id)
            ).scalar_one_or_none()
            is not None
        )


def _asset_from_row(row: RowMapping) -> Room3DAssetEntry:
    return Room3DAssetEntry(
        room_3d_asset_id=str(row["room_3d_asset_id"]),
        room_id=str(row["room_id"]),
        thread_id=str(row["thread_id"]),
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        source_asset_id=str(row["source_asset_id"]),
        usd_format=str(row["usd_format"]),
        metadata=_json_dict(row["metadata_json"]),
        created_at=str(row["created_at"]),
    )


def _snapshot_from_row(row: RowMapping) -> Room3DSnapshotEntry:
    return Room3DSnapshotEntry(
        room_3d_snapshot_id=str(row["room_3d_snapshot_id"]),
        room_id=str(row["room_id"]),
        thread_id=str(row["thread_id"]),
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        snapshot_asset_id=str(row["snapshot_asset_id"]),
        room_3d_asset_id=(
            str(row["room_3d_asset_id"]) if row["room_3d_asset_id"] is not None else None
        ),
        camera=_json_dict(row["camera_json"]),
        lighting=_json_dict(row["lighting_json"]),
        comment=str(row["comment"]) if row["comment"] is not None else None,
        created_at=str(row["created_at"]),
    )


def _json_dict(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        return {}
    return {str(key): item for key, item in parsed.items()}
