"""Persistence helpers for floor-plan revision history and confirmations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import String, cast, func, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select

from ikea_agent.persistence.models import AgentRunRecord, AssetRecord, FloorPlanRevisionRecord
from ikea_agent.persistence.ownership import ensure_thread_record
from ikea_agent.tools.floorplanner.models import FloorPlanScene

_FLOOR_PLAN_SCENE_ADAPTER = TypeAdapter(FloorPlanScene)


@dataclass(frozen=True, slots=True)
class FloorPlanRevisionSnapshot:
    """Typed projection of one persisted floor-plan revision row."""

    floor_plan_revision_id: str
    room_id: str
    thread_id: str
    revision: int
    scene_level: str
    scene: FloorPlanScene
    summary: dict[str, Any]
    svg_asset_id: str | None
    png_asset_id: str | None
    confirmed_at: str | None
    confirmed_by_run_id: str | None
    confirmation_note: str | None
    created_at: str


class FloorPlanRepository:
    """Repository for durable floor-plan revisions and explicit confirmations."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_revision(
        self,
        *,
        room_id: str,
        thread_id: str,
        scene: FloorPlanScene,
        summary: dict[str, Any],
        svg_asset_id: str | None,
        png_asset_id: str | None,
    ) -> FloorPlanRevisionSnapshot:
        """Persist one new revision and return the typed stored snapshot."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            self._ensure_thread(session=session, room_id=room_id, thread_id=thread_id, now=now)
            session.flush()
            next_revision = self._next_revision(session=session, room_id=room_id)
            revision_id = f"fprev-{room_id[:20]}-{next_revision:06d}"
            persisted_svg_asset_id = self._resolve_existing_asset_id(
                session=session, room_id=room_id, asset_id=svg_asset_id
            )
            persisted_png_asset_id = self._resolve_existing_asset_id(
                session=session, room_id=room_id, asset_id=png_asset_id
            )
            session.add(
                FloorPlanRevisionRecord(
                    floor_plan_revision_id=revision_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    revision=next_revision,
                    scene_level=scene.scene_level,
                    scene_json=json.dumps(scene.model_dump(mode="json"), sort_keys=True),
                    summary_json=json.dumps(summary, sort_keys=True),
                    svg_asset_id=persisted_svg_asset_id,
                    png_asset_id=persisted_png_asset_id,
                    confirmed_at=None,
                    confirmed_by_run_id=None,
                    confirmation_note=None,
                    created_at=now,
                )
            )
            session.commit()

        snapshot = self.get_revision(room_id=room_id, revision=next_revision)
        if snapshot is None:  # pragma: no cover - defensive guard
            msg = "Saved floor-plan revision could not be reloaded"
            raise RuntimeError(msg)
        return snapshot

    def get_latest_revision(self, *, room_id: str) -> FloorPlanRevisionSnapshot | None:
        """Load the highest revision for one room."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    _snapshot_select_statement()
                    .where(FloorPlanRevisionRecord.room_id == room_id)
                    .order_by(FloorPlanRevisionRecord.revision.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _snapshot_from_row(row)

    def get_revision(self, *, room_id: str, revision: int) -> FloorPlanRevisionSnapshot | None:
        """Load a specific revision for one room."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    _snapshot_select_statement()
                    .where(FloorPlanRevisionRecord.room_id == room_id)
                    .where(FloorPlanRevisionRecord.revision == revision)
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _snapshot_from_row(row)

    def confirm_revision(
        self,
        *,
        room_id: str,
        revision: int | None,
        run_id: str | None,
        confirmation_note: str | None,
    ) -> FloorPlanRevisionSnapshot | None:
        """Mark a revision as accepted by the user and return the updated snapshot."""

        target = (
            self.get_revision(room_id=room_id, revision=revision)
            if revision is not None
            else self.get_latest_revision(room_id=room_id)
        )
        if target is None:
            return None

        now = datetime.now(UTC)
        persisted_run_id = self._resolve_existing_run_id(run_id=run_id)
        with self._session_factory() as session:
            session.execute(
                update(FloorPlanRevisionRecord)
                .where(
                    FloorPlanRevisionRecord.floor_plan_revision_id == target.floor_plan_revision_id
                )
                .values(
                    confirmed_at=now,
                    confirmed_by_run_id=persisted_run_id,
                    confirmation_note=confirmation_note,
                )
            )
            session.commit()

        return self.get_revision(room_id=room_id, revision=target.revision)

    @staticmethod
    def _next_revision(*, session: Session, room_id: str) -> int:
        current_max = session.execute(
            select(func.max(FloorPlanRevisionRecord.revision)).where(
                FloorPlanRevisionRecord.room_id == room_id
            )
        ).scalar_one_or_none()
        return int(current_max or 0) + 1

    @staticmethod
    def _ensure_thread(*, session: Session, room_id: str, thread_id: str, now: datetime) -> None:
        ensure_thread_record(session, room_id=room_id, thread_id=thread_id, now=now)

    def _resolve_existing_run_id(self, *, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        with self._session_factory() as session:
            return session.execute(
                select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
            ).scalar_one_or_none()

    @staticmethod
    def _resolve_existing_asset_id(
        *,
        session: Session,
        room_id: str,
        asset_id: str | None,
    ) -> str | None:
        if asset_id is None:
            return None
        return session.execute(
            select(AssetRecord.asset_id)
            .where(AssetRecord.asset_id == asset_id)
            .where(AssetRecord.room_id == room_id)
        ).scalar_one_or_none()


def _snapshot_select_statement() -> Select[tuple[object, ...]]:
    return select(
        FloorPlanRevisionRecord.floor_plan_revision_id,
        FloorPlanRevisionRecord.room_id,
        FloorPlanRevisionRecord.thread_id,
        FloorPlanRevisionRecord.revision,
        FloorPlanRevisionRecord.scene_level,
        FloorPlanRevisionRecord.scene_json,
        FloorPlanRevisionRecord.summary_json,
        FloorPlanRevisionRecord.svg_asset_id,
        FloorPlanRevisionRecord.png_asset_id,
        cast(FloorPlanRevisionRecord.confirmed_at, String),
        FloorPlanRevisionRecord.confirmed_by_run_id,
        FloorPlanRevisionRecord.confirmation_note,
        cast(FloorPlanRevisionRecord.created_at, String),
    )


def _snapshot_from_row(row: RowMapping) -> FloorPlanRevisionSnapshot:
    return FloorPlanRevisionSnapshot(
        floor_plan_revision_id=str(row["floor_plan_revision_id"]),
        room_id=str(row["room_id"]),
        thread_id=str(row["thread_id"]),
        revision=int(row["revision"]),
        scene_level=str(row["scene_level"]),
        scene=_FLOOR_PLAN_SCENE_ADAPTER.validate_python(json.loads(str(row["scene_json"]))),
        summary=_as_dict(str(row["summary_json"])),
        svg_asset_id=str(row["svg_asset_id"]) if row["svg_asset_id"] is not None else None,
        png_asset_id=str(row["png_asset_id"]) if row["png_asset_id"] is not None else None,
        confirmed_at=str(row["confirmed_at"]) if row["confirmed_at"] is not None else None,
        confirmed_by_run_id=(
            str(row["confirmed_by_run_id"]) if row["confirmed_by_run_id"] is not None else None
        ),
        confirmation_note=str(row["confirmation_note"])
        if row["confirmation_note"] is not None
        else None,
        created_at=str(row["created_at"]),
    )


def _as_dict(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        return {}
    return dict(loaded)
