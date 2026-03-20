"""Room-aware query repository for UI-facing persistence APIs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal
from typing import cast as typing_cast
from uuid import uuid4

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select

from ikea_agent.chat_app.thread_api_models import (
    AnalysisFeedbackItem,
    AssetListItem,
    KnownFactItem,
    ThreadDetailItem,
    ThreadTranscriptResponse,
)
from ikea_agent.chat_app.transcript_codec import serialize_thread_transcript
from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisFeedbackRecord,
    AnalysisRunRecord,
    AssetRecord,
    BundleProposalRecord,
    FloorPlanRevisionRecord,
    RoomRecord,
    SearchRunRecord,
    ThreadRecord,
)
from ikea_agent.persistence.run_history_repository import RunHistoryRepository
from ikea_agent.shared.types import (
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    RoomType,
)

AnalysisFeedbackKind = Literal["confirm", "reject", "uncertain"]


def _floor_plan_asset_labels(session: Session, *, room_id: str) -> dict[str, str]:
    """Return readable display labels for floor-plan revision assets in one room."""

    rows = session.execute(
        select(
            FloorPlanRevisionRecord.revision,
            FloorPlanRevisionRecord.svg_asset_id,
            FloorPlanRevisionRecord.png_asset_id,
        )
        .where(FloorPlanRevisionRecord.room_id == room_id)
        .order_by(FloorPlanRevisionRecord.revision.desc())
    ).all()
    labels: dict[str, str] = {}
    for row in rows:
        revision = int(row.revision)
        if row.svg_asset_id is not None:
            labels[str(row.svg_asset_id)] = f"Floor plan revision {revision} (SVG)"
        if row.png_asset_id is not None:
            labels[str(row.png_asset_id)] = f"Floor plan revision {revision} (PNG preview)"
    return labels


class ThreadQueryRepository:
    """Query and mutation helpers for room/thread data API routes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_thread(self, *, room_id: str, thread_id: str) -> ThreadDetailItem | None:
        """Return one thread detail with aggregate child counts."""

        with self._session_factory() as session:
            row = session.execute(
                select(
                    ThreadRecord.thread_id,
                    ThreadRecord.title.label("thread_title"),
                    ThreadRecord.room_id,
                    RoomRecord.title.label("room_title"),
                    RoomRecord.room_type.label("room_type"),
                    ThreadRecord.status,
                    cast(ThreadRecord.last_activity_at, String),
                )
                .join(RoomRecord, RoomRecord.room_id == ThreadRecord.room_id)
                .where(ThreadRecord.thread_id == thread_id)
                .where(ThreadRecord.room_id == room_id)
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
                .where(AssetRecord.room_id == str(row.room_id)),
            )
            floor_plan_revision_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(FloorPlanRevisionRecord)
                .where(FloorPlanRevisionRecord.room_id == str(row.room_id)),
            )
            analysis_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(AnalysisRunRecord)
                .where(AnalysisRunRecord.room_id == str(row.room_id)),
            )
            search_count = _count_rows(
                session=session,
                statement=select(func.count())
                .select_from(SearchRunRecord)
                .where(SearchRunRecord.room_id == str(row.room_id)),
            )

        return ThreadDetailItem(
            thread_id=str(row.thread_id),
            title=str(row.thread_title) if row.thread_title is not None else None,
            room_id=str(row.room_id),
            room_title=str(row.room_title),
            room_type=typing_cast("RoomType | None", row.room_type),
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

    def list_assets(self, *, room_id: str, thread_id: str) -> list[AssetListItem] | None:
        """Return room-linked assets visible from one thread."""

        with self._session_factory() as session:
            if not _thread_exists_in_room(session=session, room_id=room_id, thread_id=thread_id):
                return None
            floor_plan_labels = _floor_plan_asset_labels(session, room_id=room_id)
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
                .where(AssetRecord.room_id == room_id)
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
                display_label=floor_plan_labels.get(str(item.asset_id)),
                mime_type=str(item.mime_type),
                file_name=str(item.file_name) if item.file_name is not None else None,
                storage_path=str(item.storage_path),
                size_bytes=int(item.size_bytes),
                created_at=str(item.created_at) if item.created_at is not None else None,
            )
            for item in rows
        ]

    def list_bundle_proposals(
        self,
        *,
        room_id: str,
        thread_id: str,
    ) -> list[BundleProposalToolResult] | None:
        """Return persisted bundle proposals visible from one thread."""

        with self._session_factory() as session:
            if not _thread_exists_in_room(session=session, room_id=room_id, thread_id=thread_id):
                return None
            rows = session.execute(
                select(
                    BundleProposalRecord.bundle_id,
                    BundleProposalRecord.run_id,
                    BundleProposalRecord.title,
                    BundleProposalRecord.notes,
                    BundleProposalRecord.budget_cap_eur,
                    BundleProposalRecord.bundle_total_eur,
                    BundleProposalRecord.items_json,
                    BundleProposalRecord.validations_json,
                    cast(BundleProposalRecord.created_at, String),
                )
                .where(BundleProposalRecord.room_id == room_id)
                .order_by(BundleProposalRecord.created_at.desc())
            ).all()
        return [
            BundleProposalToolResult(
                bundle_id=str(item.bundle_id),
                title=str(item.title),
                notes=str(item.notes) if item.notes is not None else None,
                budget_cap_eur=(
                    float(item.budget_cap_eur) if item.budget_cap_eur is not None else None
                ),
                items=_as_bundle_items(item.items_json),
                bundle_total_eur=(
                    float(item.bundle_total_eur) if item.bundle_total_eur is not None else None
                ),
                validations=_as_bundle_validations(item.validations_json),
                created_at=str(item.created_at) if item.created_at is not None else "",
                run_id=str(item.run_id) if item.run_id is not None else None,
            )
            for item in rows
        ]

    def list_known_facts(self, *, room_id: str, thread_id: str) -> list[KnownFactItem] | None:
        """Return room/project facts visible from one thread."""

        with self._session_factory() as session:
            if not _thread_exists_in_room(session=session, room_id=room_id, thread_id=thread_id):
                return None

        rows = ContextFactRepository(self._session_factory).list_known_facts_for_thread(
            thread_id=thread_id
        )
        return [
            KnownFactItem(
                fact_id=item.fact_id,
                scope=item.scope,
                kind=item.kind,
                summary=item.summary,
                source_message_text=item.source_message_text,
                updated_at=item.updated_at,
                run_id=item.run_id,
            )
            for item in rows
        ]

    def get_transcript(
        self,
        *,
        room_id: str,
        thread_id: str,
    ) -> ThreadTranscriptResponse | None:
        """Return the canonical transcript payload for one room/thread pair."""

        with self._session_factory() as session:
            if not _thread_exists_in_room(session=session, room_id=room_id, thread_id=thread_id):
                return None

        messages = RunHistoryRepository(self._session_factory).load_message_history(
            thread_id=thread_id
        )
        return ThreadTranscriptResponse(
            room_id=room_id,
            thread_id=thread_id,
            messages=serialize_thread_transcript(messages),
        )

    def create_analysis_feedback(
        self,
        *,
        room_id: str,
        thread_id: str,
        analysis_id: str,
        feedback_kind: AnalysisFeedbackKind,
        mask_ordinal: int | None,
        mask_label: str | None,
        query_text: str | None,
        note: str | None,
        run_id: str | None,
    ) -> AnalysisFeedbackItem | None:
        """Persist one analysis feedback row when the analysis exists for the room."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            if not _thread_exists_in_room(session=session, room_id=room_id, thread_id=thread_id):
                return None
            analysis_exists = session.execute(
                select(AnalysisRunRecord.analysis_id)
                .where(AnalysisRunRecord.room_id == room_id)
                .where(AnalysisRunRecord.analysis_id == analysis_id)
            ).scalar_one_or_none()
            if analysis_exists is None:
                return None
            persisted_run_id = _resolve_existing_run_id(session=session, run_id=run_id)
            feedback_id = f"analysis-fbk-{uuid4().hex[:24]}"
            session.add(
                AnalysisFeedbackRecord(
                    analysis_feedback_id=feedback_id,
                    analysis_id=analysis_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    feedback_kind=feedback_kind,
                    mask_ordinal=mask_ordinal,
                    mask_label=mask_label,
                    query_text=query_text,
                    note=note,
                    created_at=now,
                )
            )
            session.commit()
            return AnalysisFeedbackItem(
                analysis_feedback_id=feedback_id,
                analysis_id=analysis_id,
                thread_id=thread_id,
                run_id=persisted_run_id,
                feedback_kind=feedback_kind,
                mask_ordinal=mask_ordinal,
                mask_label=mask_label,
                query_text=query_text,
                note=note,
                created_at=now.isoformat(),
            )


def _count_rows(*, session: Session, statement: Select[tuple[int]]) -> int:
    count_value = session.execute(statement).scalar_one()
    return int(count_value)


def _thread_exists_in_room(*, session: Session, room_id: str, thread_id: str) -> bool:
    return (
        session.execute(
            select(ThreadRecord.thread_id)
            .where(ThreadRecord.thread_id == thread_id)
            .where(ThreadRecord.room_id == room_id)
        ).scalar_one_or_none()
        is not None
    )


def _run_exists(*, session: Session, run_id: str) -> bool:
    return (
        session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()
        is not None
    )


def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
    if run_id is None:
        return None
    return run_id if _run_exists(session=session, run_id=run_id) else None


def _as_bundle_items(value: object) -> list[BundleProposalLineItem]:
    if not isinstance(value, str):
        return []
    loaded = json.loads(value)
    if not isinstance(loaded, list):
        return []
    return [BundleProposalLineItem.model_validate(item) for item in loaded]


def _as_bundle_validations(value: object) -> list[BundleValidationResult]:
    if not isinstance(value, str):
        return []
    loaded = json.loads(value)
    if not isinstance(loaded, list):
        return []
    return [BundleValidationResult.model_validate(item) for item in loaded]
