from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisFeedbackRecord,
    AnalysisRunRecord,
    AssetRecord,
    BundleProposalRecord,
    FloorPlanRevisionRecord,
    ProjectFactRecord,
    RoomFactRecord,
    SearchRunRecord,
    ThreadMessageSegmentRecord,
    ThreadRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.ownership import ensure_default_dev_hierarchy
from ikea_agent.persistence.run_history_repository import RunHistoryRepository
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository


@dataclass
class _RuntimeStub:
    sqlalchemy_engine: object
    session_factory: sessionmaker[Session]


def _runtime(tmp_path: Path) -> _RuntimeStub:
    engine = create_sqlite_engine(tmp_path / "thread_api_test.sqlite")
    ensure_persistence_schema(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _RuntimeStub(sqlalchemy_engine=engine, session_factory=session_factory)


def _encoded_messages_json() -> str:
    return ModelMessagesTypeAdapter.dump_json(
        [
            ModelRequest(parts=[UserPromptPart(content="Need help with layout.")]),
            ModelResponse(parts=[TextPart(content="Let's measure the walls.")]),
        ]
    ).decode("utf-8")


def _seed(runtime: _RuntimeStub, *, tmp_path: Path) -> None:
    now = datetime.now(UTC)
    with runtime.session_factory() as session:
        hierarchy = ensure_default_dev_hierarchy(session, now=now)
        session.add(
            ThreadRecord(
                thread_id="thread-api",
                room_id=hierarchy.room_id,
                title="Initial title",
                status="active",
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
        )
        session.add(
            ThreadRecord(
                thread_id="thread-api-followup",
                room_id=hierarchy.room_id,
                title="Follow-up thread",
                status="active",
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
        )
        session.flush()
        session.add(
            AgentRunRecord(
                run_id="run-api",
                thread_id="thread-api",
                parent_run_id=None,
                status="completed",
                user_prompt_text="prompt",
                error_message=None,
                started_at=now,
                ended_at=now,
            )
        )
        session.add(
            ThreadMessageSegmentRecord(
                thread_message_segment_id="msgseg-api",
                thread_id="thread-api",
                run_id="run-api",
                sequence_no=1,
                messages_json=_encoded_messages_json(),
                created_at=now,
            )
        )
        session.add(
            AssetRecord(
                asset_id="asset-api",
                room_id=hierarchy.room_id,
                thread_id="thread-api",
                run_id="run-api",
                created_by_tool="upload",
                kind="user_upload",
                mime_type="image/png",
                file_name="room.png",
                storage_path=str(tmp_path / "room.png"),
                sha256="abc",
                size_bytes=123,
                width=None,
                height=None,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            FloorPlanRevisionRecord(
                floor_plan_revision_id="fprev-api",
                room_id=hierarchy.room_id,
                thread_id="thread-api",
                revision=1,
                scene_level="baseline",
                scene_json="{}",
                summary_json='{"wall_count": 3}',
                svg_asset_id="asset-api",
                png_asset_id="asset-api",
                confirmed_at=now,
                confirmed_by_run_id="run-api",
                confirmation_note="confirmed",
                created_at=now,
            )
        )
        session.add(
            AnalysisRunRecord(
                analysis_id="analysis-api",
                room_id=hierarchy.room_id,
                thread_id="thread-api",
                run_id="run-api",
                tool_name="detect_objects_in_image",
                input_asset_id="asset-api",
                request_json="{}",
                result_json="{}",
                created_at=now,
            )
        )
        session.add(
            SearchRunRecord(
                search_id="search-api",
                room_id=hierarchy.room_id,
                thread_id="thread-api",
                run_id="run-api",
                query_text="wardrobe",
                filters_json="{}",
                warning_json=None,
                total_candidates=10,
                returned_count=1,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            BundleProposalRecord(
                bundle_id="bundle-api",
                room_id=hierarchy.room_id,
                thread_id="thread-api",
                run_id="run-api",
                title="Desk starter",
                notes="Persisted bundle proposal",
                budget_cap_eur=250.0,
                bundle_total_eur=199.0,
                items_json=json.dumps(
                    [
                        {
                            "item_id": "prod-1",
                            "product_name": "PAX",
                            "description_text": "Slim wardrobe",
                            "price_eur": 199.0,
                            "quantity": 1,
                            "line_total_eur": 199.0,
                            "reason": "Primary storage",
                        }
                    ]
                ),
                validations_json=json.dumps(
                    [
                        {
                            "kind": "budget_max_eur",
                            "status": "pass",
                            "message": "Bundle total €199.00 is within budget cap €250.00.",
                        }
                    ]
                ),
                created_at=now,
            )
        )
        session.add(
            RoomFactRecord(
                room_fact_id="rfact-api",
                room_id=hierarchy.room_id,
                run_id="run-api",
                signal_key="agent_note",
                kind="constraint",
                value="user_has_toddlers",
                summary="User has toddlers, keep things elevated.",
                source_message_text="We have a toddler at home.",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ProjectFactRecord(
                project_fact_id="pfact-api",
                project_id=hierarchy.project_id,
                run_id="run-api",
                signal_key="agent_note",
                kind="fact",
                value="household_has_toddler",
                summary="Household includes a toddler.",
                source_message_text="We have a toddler at home.",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


def test_thread_query_repository_returns_room_visible_records(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _seed(runtime, tmp_path=tmp_path)
    repository = ThreadQueryRepository(runtime.session_factory)

    detail = repository.get_thread(room_id="room-dev-default", thread_id="thread-api")
    assets = repository.list_assets(room_id="room-dev-default", thread_id="thread-api")
    bundles = repository.list_bundle_proposals(room_id="room-dev-default", thread_id="thread-api")
    known_facts = repository.list_known_facts(room_id="room-dev-default", thread_id="thread-api")

    assert detail is not None
    assert assets is not None
    assert bundles is not None
    assert known_facts is not None
    assert detail.thread_id == "thread-api"
    assert detail.room_id == "room-dev-default"
    assert detail.room_title == "Untitled room"
    assert detail.asset_count == 1
    assert detail.run_count == 1
    assert detail.floor_plan_revision_count == 1
    assert detail.analysis_count == 1
    assert detail.search_count == 1

    assert len(assets) == 1
    assert assets[0].asset_id == "asset-api"
    assert assets[0].uri == "/attachments/asset-api"
    assert assets[0].created_by_tool == "upload"
    assert assets[0].display_label == "Floor plan revision 1 (PNG preview)"

    assert len(bundles) == 1
    assert bundles[0].bundle_id == "bundle-api"
    assert bundles[0].items[0].item_id == "prod-1"
    assert bundles[0].items[0].image_urls == []
    assert bundles[0].validations[0].kind == "budget_max_eur"

    assert len(known_facts) == 2
    assert known_facts[0].scope == "room"
    assert known_facts[0].kind == "constraint"
    assert known_facts[0].summary == "User has toddlers, keep things elevated."
    assert known_facts[1].scope == "project"

    followup_detail = repository.get_thread(
        room_id="room-dev-default",
        thread_id="thread-api-followup",
    )
    followup_assets = repository.list_assets(
        room_id="room-dev-default",
        thread_id="thread-api-followup",
    )
    followup_bundles = repository.list_bundle_proposals(
        room_id="room-dev-default",
        thread_id="thread-api-followup",
    )

    assert followup_detail is not None
    assert followup_assets is not None
    assert followup_bundles is not None
    assert followup_detail.asset_count == 1
    assert followup_detail.floor_plan_revision_count == 1
    assert followup_detail.analysis_count == 1
    assert followup_detail.search_count == 1
    assert [item.asset_id for item in followup_assets] == ["asset-api"]
    assert [item.bundle_id for item in followup_bundles] == ["bundle-api"]


def test_thread_query_repository_keeps_transcripts_thread_specific(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _seed(runtime, tmp_path=tmp_path)
    repository = ThreadQueryRepository(runtime.session_factory)

    transcript = repository.get_transcript(room_id="room-dev-default", thread_id="thread-api")
    followup_transcript = repository.get_transcript(
        room_id="room-dev-default",
        thread_id="thread-api-followup",
    )
    mismatched_assets = repository.list_assets(room_id="room-other", thread_id="thread-api")

    assert transcript is not None
    assert followup_transcript is not None
    assert transcript.room_id == "room-dev-default"
    assert transcript.thread_id == "thread-api"
    assert transcript.messages == [
        {
            "content": "Need help with layout.",
            "id": "user-1",
            "role": "user",
        },
        {
            "content": "Let's measure the walls.",
            "id": "assistant-2",
            "role": "assistant",
        },
    ]
    assert followup_transcript.messages == []
    assert mismatched_assets is None


def test_thread_query_repository_orders_threads_by_latest_durable_activity(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    base_now = datetime.now(UTC) - timedelta(hours=1)
    with runtime.session_factory() as session:
        hierarchy = ensure_default_dev_hierarchy(session, now=base_now)
        session.add(
            ThreadRecord(
                thread_id="thread-stale",
                room_id=hierarchy.room_id,
                title="Stale thread",
                status="active",
                created_at=base_now,
                updated_at=base_now,
                last_activity_at=base_now,
            )
        )
        fresher_time = base_now + timedelta(minutes=5)
        session.add(
            ThreadRecord(
                thread_id="thread-fresh",
                room_id=hierarchy.room_id,
                title="Fresh thread",
                status="active",
                created_at=fresher_time,
                updated_at=fresher_time,
                last_activity_at=fresher_time,
            )
        )
        session.commit()

    RunHistoryRepository(runtime.session_factory).record_run_start(
        room_id="room-dev-default",
        thread_id="thread-stale",
        run_id="run-ordering",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="Re-open this thread",
    )

    threads = ThreadQueryRepository(runtime.session_factory).list_threads(
        room_id="room-dev-default"
    )

    assert [item.thread_id for item in threads[:2]] == ["thread-stale", "thread-fresh"]


def test_create_analysis_feedback_persists_thread_scoped_records(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _seed(runtime, tmp_path=tmp_path)
    repository = ThreadQueryRepository(runtime.session_factory)

    created = repository.create_analysis_feedback(
        room_id="room-dev-default",
        thread_id="thread-api-followup",
        analysis_id="analysis-api",
        feedback_kind="confirm",
        mask_ordinal=1,
        mask_label="bed",
        query_text="bed",
        note="Looks correct.",
        run_id="run-api",
    )
    missing = repository.create_analysis_feedback(
        room_id="room-dev-default",
        thread_id="thread-api",
        analysis_id="analysis-missing",
        feedback_kind="reject",
        mask_ordinal=None,
        mask_label=None,
        query_text=None,
        note=None,
        run_id=None,
    )

    assert created is not None
    assert created.feedback_kind == "confirm"
    assert created.mask_label == "bed"
    assert created.run_id == "run-api"
    assert missing is None

    with runtime.session_factory() as session:
        persisted = session.execute(
            select(
                AnalysisFeedbackRecord.analysis_id,
                AnalysisFeedbackRecord.thread_id,
                AnalysisFeedbackRecord.query_text,
            ).where(AnalysisFeedbackRecord.analysis_feedback_id == created.analysis_feedback_id)
        ).one()

    assert persisted.analysis_id == "analysis-api"
    assert persisted.thread_id == "thread-api-followup"
    assert persisted.query_text == "bed"
