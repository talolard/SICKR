"""Persistence helpers for image-analysis runs and normalized detections."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import String, cast, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisDetectionRecord,
    AnalysisInputAssetRecord,
    AnalysisRunRecord,
    AssetRecord,
)
from ikea_agent.persistence.ownership import require_thread_record
from ikea_agent.tools.image_analysis.models import DetectedObject


@dataclass(frozen=True, slots=True)
class RoomImageAnalysisSnapshot:
    """Typed projection of one persisted room image analysis row."""

    analysis_id: str
    room_id: str
    thread_id: str
    run_id: str | None
    tool_name: str
    input_asset_id: str
    input_asset_ids: tuple[str, ...]
    request: dict[str, object]
    result: dict[str, object]
    created_at: str


class AnalysisRepository:
    """Repository for durable image-analysis outputs linked to source assets."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_analysis(
        self,
        *,
        tool_name: str,
        room_id: str,
        thread_id: str,
        run_id: str | None,
        input_asset_id: str,
        input_asset_ids: list[str] | None = None,
        request_json: dict[str, object],
        result_json: dict[str, object],
        detections: list[DetectedObject],
    ) -> str | None:
        """Persist one analysis row and optional normalized detections.

        Returns the analysis id when persisted, or `None` when required parent rows
        are missing (for example stale input asset references).
        """

        now = datetime.now(UTC)
        resolved_input_asset_ids = input_asset_ids or [input_asset_id]
        with self._session_factory() as session:
            if not self._all_assets_exist(
                session=session,
                room_id=room_id,
                asset_ids=resolved_input_asset_ids,
            ):
                return None
            require_thread_record(session, room_id=room_id, thread_id=thread_id)

            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)
            analysis_id = f"analysis-{uuid4().hex[:24]}"
            session.add(
                AnalysisRunRecord(
                    analysis_id=analysis_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    tool_name=tool_name,
                    input_asset_id=input_asset_id,
                    request_json=json.dumps(request_json, sort_keys=True),
                    result_json=json.dumps(result_json, sort_keys=True),
                    created_at=now,
                )
            )
            session.flush()
            for index, asset_id in enumerate(resolved_input_asset_ids):
                session.add(
                    AnalysisInputAssetRecord(
                        analysis_input_asset_id=f"ain-{analysis_id[-20:]}-{index + 1:04d}",
                        analysis_id=analysis_id,
                        asset_id=asset_id,
                        ordinal=index,
                    )
                )
            for index, detection in enumerate(detections):
                x1, y1, x2, y2 = detection.bbox_xyxy_px
                nx1, ny1, nx2, ny2 = detection.bbox_xyxy_norm
                session.add(
                    AnalysisDetectionRecord(
                        analysis_detection_id=f"det-{analysis_id[-20:]}-{index + 1:04d}",
                        analysis_id=analysis_id,
                        ordinal=index + 1,
                        label=detection.label,
                        bbox_x1_px=x1,
                        bbox_y1_px=y1,
                        bbox_x2_px=x2,
                        bbox_y2_px=y2,
                        bbox_x1_norm=nx1,
                        bbox_y1_norm=ny1,
                        bbox_x2_norm=nx2,
                        bbox_y2_norm=ny2,
                    )
                )
            session.commit()
            return analysis_id

    def list_room_analyses(self, *, room_id: str) -> list[RoomImageAnalysisSnapshot]:
        """Return persisted image analyses for one room ordered newest-first."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        AnalysisRunRecord.analysis_id,
                        AnalysisRunRecord.room_id,
                        AnalysisRunRecord.thread_id,
                        AnalysisRunRecord.run_id,
                        AnalysisRunRecord.tool_name,
                        AnalysisRunRecord.input_asset_id,
                        AnalysisRunRecord.request_json,
                        AnalysisRunRecord.result_json,
                        cast(AnalysisRunRecord.created_at, String).label("created_at"),
                    )
                    .where(AnalysisRunRecord.room_id == room_id)
                    .order_by(AnalysisRunRecord.created_at.desc())
                )
                .mappings()
                .all()
            )
            if not rows:
                return []

            analysis_ids = [str(row["analysis_id"]) for row in rows]
            input_asset_rows = session.execute(
                select(
                    AnalysisInputAssetRecord.analysis_id,
                    AnalysisInputAssetRecord.asset_id,
                    AnalysisInputAssetRecord.ordinal,
                )
                .where(AnalysisInputAssetRecord.analysis_id.in_(analysis_ids))
                .order_by(
                    AnalysisInputAssetRecord.analysis_id.asc(),
                    AnalysisInputAssetRecord.ordinal.asc(),
                )
            ).all()

        input_asset_ids_by_analysis: dict[str, list[str]] = {
            analysis_id: [] for analysis_id in analysis_ids
        }
        for row in input_asset_rows:
            input_asset_ids_by_analysis.setdefault(str(row.analysis_id), []).append(
                str(row.asset_id)
            )

        return [
            _analysis_snapshot_from_row(
                row,
                input_asset_ids=tuple(
                    input_asset_ids_by_analysis.get(
                        str(row["analysis_id"]), [str(row["input_asset_id"])]
                    )
                ),
            )
            for row in rows
        ]

    @staticmethod
    def _all_assets_exist(*, session: Session, room_id: str, asset_ids: list[str]) -> bool:
        existing_asset_ids = session.execute(
            select(AssetRecord.asset_id)
            .where(AssetRecord.asset_id.in_(asset_ids))
            .where(AssetRecord.room_id == room_id)
        ).scalars()
        return len(set(existing_asset_ids)) == len(set(asset_ids))

    @staticmethod
    def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        return session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()


def _analysis_snapshot_from_row(
    row: RowMapping,
    *,
    input_asset_ids: tuple[str, ...],
) -> RoomImageAnalysisSnapshot:
    return RoomImageAnalysisSnapshot(
        analysis_id=str(row["analysis_id"]),
        room_id=str(row["room_id"]),
        thread_id=str(row["thread_id"]),
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        tool_name=str(row["tool_name"]),
        input_asset_id=str(row["input_asset_id"]),
        input_asset_ids=input_asset_ids,
        request=_json_dict(row["request_json"]),
        result=_json_dict(row["result_json"]),
        created_at=str(row["created_at"]),
    )


def _json_dict(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        return {}
    return {str(key): item for key, item in parsed.items()}
