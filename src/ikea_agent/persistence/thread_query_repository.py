"""Thread-scoped query repository for UI-facing persistence APIs."""

from __future__ import annotations

import json

from sqlalchemy import String, cast, func, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select

from ikea_agent.chat_app.thread_api_models import (
    AnalysisListItem,
    AssetListItem,
    DetectionListItem,
    FloorPlanRevisionListItem,
    ThreadDetailItem,
    ThreadListItem,
)
from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisDetectionRecord,
    AnalysisRunRecord,
    AssetRecord,
    FloorPlanRevisionRecord,
    SearchRunRecord,
    ThreadRecord,
)


class ThreadQueryRepository:
    """Query and mutation helpers for thread data API routes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_threads(self, *, limit: int = 200) -> list[ThreadListItem]:
        """Return latest threads sorted by activity."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    ThreadRecord.thread_id,
                    ThreadRecord.title,
                    ThreadRecord.status,
                    cast(ThreadRecord.last_activity_at, String),
                )
                .order_by(ThreadRecord.last_activity_at.desc())
                .limit(limit)
            ).all()
        return [
            ThreadListItem(
                thread_id=str(item.thread_id),
                title=str(item.title) if item.title is not None else None,
                status=str(item.status),
                last_activity_at=(
                    str(item.last_activity_at) if item.last_activity_at is not None else None
                ),
            )
            for item in rows
        ]

    def get_thread(self, *, thread_id: str) -> ThreadDetailItem | None:
        """Return one thread detail with aggregate child counts."""

        with self._session_factory() as session:
            row = session.execute(
                select(
                    ThreadRecord.thread_id,
                    ThreadRecord.title,
                    ThreadRecord.status,
                    cast(ThreadRecord.last_activity_at, String),
                ).where(ThreadRecord.thread_id == thread_id)
            ).one_or_none()
            if row is None:
                return None
            run_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(AgentRunRecord)
                .where(AgentRunRecord.thread_id == thread_id),
            )
            asset_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(AssetRecord)
                .where(AssetRecord.thread_id == thread_id),
            )
            floor_plan_revision_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(FloorPlanRevisionRecord)
                .where(FloorPlanRevisionRecord.thread_id == thread_id),
            )
            analysis_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(AnalysisRunRecord)
                .where(AnalysisRunRecord.thread_id == thread_id),
            )
            search_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(SearchRunRecord)
                .where(SearchRunRecord.thread_id == thread_id),
            )

        return ThreadDetailItem(
            thread_id=str(row.thread_id),
            title=str(row.title) if row.title is not None else None,
            status=str(row.status),
            last_activity_at=(
                str(row.last_activity_at) if row.last_activity_at is not None else None
            ),
            run_count=run_count,
            asset_count=asset_count,
            floor_plan_revision_count=floor_plan_revision_count,
            analysis_count=analysis_count,
            search_count=search_count,
        )

    def update_thread_title(self, *, thread_id: str, title: str | None) -> ThreadDetailItem | None:
        """Set thread title and return the resulting detail."""

        with self._session_factory() as session:
            session.execute(
                update(ThreadRecord).where(ThreadRecord.thread_id == thread_id).values(title=title)
            )
            session.commit()
        return self.get_thread(thread_id=thread_id)

    def list_assets(self, *, thread_id: str) -> list[AssetListItem]:
        """Return thread-linked assets ordered by creation time descending."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    AssetRecord.asset_id,
                    AssetRecord.run_id,
                    AssetRecord.created_by_tool,
                    AssetRecord.kind,
                    AssetRecord.mime_type,
                    AssetRecord.file_name,
                    AssetRecord.storage_path,
                    AssetRecord.size_bytes,
                    cast(AssetRecord.created_at, String),
                )
                .where(AssetRecord.thread_id == thread_id)
                .order_by(AssetRecord.created_at.desc())
            ).all()
        return [
            AssetListItem(
                asset_id=str(item.asset_id),
                run_id=str(item.run_id) if item.run_id is not None else None,
                created_by_tool=(
                    str(item.created_by_tool) if item.created_by_tool is not None else None
                ),
                kind=str(item.kind),
                mime_type=str(item.mime_type),
                file_name=str(item.file_name) if item.file_name is not None else None,
                storage_path=str(item.storage_path),
                size_bytes=int(item.size_bytes),
                created_at=str(item.created_at) if item.created_at is not None else None,
            )
            for item in rows
        ]

    def list_floor_plan_revisions(self, *, thread_id: str) -> list[FloorPlanRevisionListItem]:
        """Return floor-plan revision rows for one thread."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(
                        FloorPlanRevisionRecord.floor_plan_revision_id,
                        FloorPlanRevisionRecord.revision,
                        FloorPlanRevisionRecord.scene_level,
                        FloorPlanRevisionRecord.svg_asset_id,
                        FloorPlanRevisionRecord.png_asset_id,
                        cast(FloorPlanRevisionRecord.confirmed_at, String),
                        FloorPlanRevisionRecord.confirmed_by_run_id,
                        FloorPlanRevisionRecord.confirmation_note,
                        FloorPlanRevisionRecord.summary_json,
                        cast(FloorPlanRevisionRecord.created_at, String),
                    )
                    .where(FloorPlanRevisionRecord.thread_id == thread_id)
                    .order_by(FloorPlanRevisionRecord.revision.desc())
                )
                .mappings()
                .all()
            )
        return [
            FloorPlanRevisionListItem(
                floor_plan_revision_id=str(item["floor_plan_revision_id"]),
                revision=int(item["revision"]),
                scene_level=str(item["scene_level"]),
                svg_asset_id=(
                    str(item["svg_asset_id"]) if item["svg_asset_id"] is not None else None
                ),
                png_asset_id=(
                    str(item["png_asset_id"]) if item["png_asset_id"] is not None else None
                ),
                confirmed_at=(
                    str(item["confirmed_at"]) if item["confirmed_at"] is not None else None
                ),
                confirmed_by_run_id=(
                    str(item["confirmed_by_run_id"])
                    if item["confirmed_by_run_id"] is not None
                    else None
                ),
                confirmation_note=(
                    str(item["confirmation_note"])
                    if item["confirmation_note"] is not None
                    else None
                ),
                summary=_as_summary_dict(item["summary_json"]),
                created_at=str(item["created_at"]) if item["created_at"] is not None else None,
            )
            for item in rows
        ]

    def list_analyses(self, *, thread_id: str) -> list[AnalysisListItem]:
        """Return image analysis rows for one thread."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    AnalysisRunRecord.analysis_id,
                    AnalysisRunRecord.run_id,
                    AnalysisRunRecord.tool_name,
                    AnalysisRunRecord.input_asset_id,
                    cast(AnalysisRunRecord.created_at, String),
                )
                .where(AnalysisRunRecord.thread_id == thread_id)
                .order_by(AnalysisRunRecord.created_at.desc())
            ).all()
        return [
            AnalysisListItem(
                analysis_id=str(item.analysis_id),
                run_id=str(item.run_id) if item.run_id is not None else None,
                tool_name=str(item.tool_name),
                input_asset_id=str(item.input_asset_id),
                created_at=str(item.created_at) if item.created_at is not None else None,
            )
            for item in rows
        ]

    def list_detections_for_image(
        self,
        *,
        thread_id: str,
        input_asset_id: str,
    ) -> list[DetectionListItem]:
        """Return normalized detections for analyses run on one source image."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    AnalysisDetectionRecord.analysis_detection_id,
                    AnalysisDetectionRecord.analysis_id,
                    AnalysisDetectionRecord.ordinal,
                    AnalysisDetectionRecord.label,
                    AnalysisDetectionRecord.bbox_x1_px,
                    AnalysisDetectionRecord.bbox_y1_px,
                    AnalysisDetectionRecord.bbox_x2_px,
                    AnalysisDetectionRecord.bbox_y2_px,
                    AnalysisDetectionRecord.bbox_x1_norm,
                    AnalysisDetectionRecord.bbox_y1_norm,
                    AnalysisDetectionRecord.bbox_x2_norm,
                    AnalysisDetectionRecord.bbox_y2_norm,
                )
                .join(
                    AnalysisRunRecord,
                    AnalysisRunRecord.analysis_id == AnalysisDetectionRecord.analysis_id,
                )
                .where(AnalysisRunRecord.thread_id == thread_id)
                .where(AnalysisRunRecord.input_asset_id == input_asset_id)
                .order_by(AnalysisDetectionRecord.ordinal.asc())
            ).all()

        return [
            DetectionListItem(
                analysis_detection_id=str(item.analysis_detection_id),
                analysis_id=str(item.analysis_id),
                ordinal=int(item.ordinal),
                label=str(item.label),
                bbox_x1_px=int(item.bbox_x1_px),
                bbox_y1_px=int(item.bbox_y1_px),
                bbox_x2_px=int(item.bbox_x2_px),
                bbox_y2_px=int(item.bbox_y2_px),
                bbox_x1_norm=float(item.bbox_x1_norm),
                bbox_y1_norm=float(item.bbox_y1_norm),
                bbox_x2_norm=float(item.bbox_x2_norm),
                bbox_y2_norm=float(item.bbox_y2_norm),
            )
            for item in rows
        ]


def _count_rows(*, session: Session, statement: Select[tuple[int]]) -> int:
    count_value = session.execute(statement).scalar_one()
    return int(count_value)


def _as_summary_dict(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        return {}
    return {str(key): item for key, item in loaded.items()}
