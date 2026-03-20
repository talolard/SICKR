"""Persistence helpers for image-analysis runs and normalized detections."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisDetectionRecord,
    AnalysisInputAssetRecord,
    AnalysisRunRecord,
    AssetRecord,
)
from ikea_agent.persistence.ownership import ensure_thread_record
from ikea_agent.tools.image_analysis.models import DetectedObject


class AnalysisRepository:
    """Repository for durable image-analysis outputs linked to source assets."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_analysis(
        self,
        *,
        tool_name: str,
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
            if not self._all_assets_exist(session=session, asset_ids=resolved_input_asset_ids):
                return None
            self._ensure_thread(session=session, thread_id=thread_id, now=now)
            session.flush()

            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)
            analysis_id = f"analysis-{uuid4().hex[:24]}"
            session.add(
                AnalysisRunRecord(
                    analysis_id=analysis_id,
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

    @staticmethod
    def _all_assets_exist(*, session: Session, asset_ids: list[str]) -> bool:
        existing_asset_ids = session.execute(
            select(AssetRecord.asset_id).where(AssetRecord.asset_id.in_(asset_ids))
        ).scalars()
        return len(set(existing_asset_ids)) == len(set(asset_ids))

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
