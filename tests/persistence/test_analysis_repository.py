from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import (
    AnalysisDetectionRecord,
    AnalysisInputAssetRecord,
    AnalysisRunRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.ownership import DEFAULT_DEV_ROOM_ID
from ikea_agent.tools.image_analysis.models import DetectedObject


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "analysis_repository_test.sqlite")
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_record_analysis_persists_run_and_detection_rows(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    asset_repository = AssetRepository(session_factory)
    store = AttachmentStore(tmp_path / "artifacts", asset_repository=asset_repository)

    with store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
    ):
        source = store.save_image_bytes(
            content=b"source-image",
            mime_type="image/png",
            filename="source.png",
            kind="user_upload",
        )

    repository = AnalysisRepository(session_factory)
    analysis_id = repository.record_analysis(
        tool_name="detect_objects_in_image",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
        input_asset_id=source.ref.attachment_id,
        request_json={"image": {"attachment_id": source.ref.attachment_id}},
        result_json={"detections": [{"label": "chair"}]},
        detections=[
            DetectedObject(
                label="chair",
                bbox_xyxy_px=(10, 20, 110, 220),
                bbox_xyxy_norm=(0.05, 0.1, 0.55, 0.9),
            )
        ],
    )

    assert analysis_id is not None

    with session_factory() as session:
        analysis_row = session.execute(
            select(
                AnalysisRunRecord.analysis_id,
                AnalysisRunRecord.room_id,
                AnalysisRunRecord.thread_id,
                AnalysisRunRecord.input_asset_id,
                AnalysisRunRecord.tool_name,
            ).where(AnalysisRunRecord.analysis_id == analysis_id)
        ).one()
        detection_row = session.execute(
            select(
                AnalysisDetectionRecord.analysis_id,
                AnalysisDetectionRecord.ordinal,
                AnalysisDetectionRecord.label,
                AnalysisDetectionRecord.bbox_x1_px,
                AnalysisDetectionRecord.bbox_y1_px,
                AnalysisDetectionRecord.bbox_x2_px,
                AnalysisDetectionRecord.bbox_y2_px,
            ).where(AnalysisDetectionRecord.analysis_id == analysis_id)
        ).one()
        input_asset_rows = session.execute(
            select(
                AnalysisInputAssetRecord.asset_id,
                AnalysisInputAssetRecord.ordinal,
            ).where(AnalysisInputAssetRecord.analysis_id == analysis_id)
        ).all()

    assert analysis_row.room_id == DEFAULT_DEV_ROOM_ID
    assert analysis_row.thread_id == "thread-analysis"
    assert analysis_row.input_asset_id == source.ref.attachment_id
    assert analysis_row.tool_name == "detect_objects_in_image"
    assert [(row.asset_id, row.ordinal) for row in input_asset_rows] == [
        (source.ref.attachment_id, 0)
    ]
    assert detection_row.ordinal == 1
    assert detection_row.label == "chair"
    assert (
        detection_row.bbox_x1_px,
        detection_row.bbox_y1_px,
        detection_row.bbox_x2_px,
        detection_row.bbox_y2_px,
    ) == (10, 20, 110, 220)


def test_record_analysis_returns_none_for_missing_input_asset(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = AnalysisRepository(session_factory)

    analysis_id = repository.record_analysis(
        tool_name="estimate_depth_map",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
        input_asset_id="missing-asset",
        request_json={"image": {"attachment_id": "missing-asset"}},
        result_json={"depth_image": None},
        detections=[],
    )

    assert analysis_id is None


def test_record_analysis_persists_multiple_input_assets_in_order(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    asset_repository = AssetRepository(session_factory)
    store = AttachmentStore(tmp_path / "artifacts", asset_repository=asset_repository)

    with store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
    ):
        first = store.save_image_bytes(
            content=b"first-image",
            mime_type="image/png",
            filename="first.png",
            kind="user_upload",
        )
        second = store.save_image_bytes(
            content=b"second-image",
            mime_type="image/png",
            filename="second.png",
            kind="user_upload",
        )

    repository = AnalysisRepository(session_factory)
    analysis_id = repository.record_analysis(
        tool_name="get_room_detail_details_from_photo",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
        input_asset_id=first.ref.attachment_id,
        input_asset_ids=[first.ref.attachment_id, second.ref.attachment_id],
        request_json={"images": [first.ref.attachment_id, second.ref.attachment_id]},
        result_json={"room_type": "living_room"},
        detections=[],
    )

    assert analysis_id is not None

    with session_factory() as session:
        rows = session.execute(
            select(
                AnalysisInputAssetRecord.asset_id,
                AnalysisInputAssetRecord.ordinal,
            )
            .where(AnalysisInputAssetRecord.analysis_id == analysis_id)
            .order_by(AnalysisInputAssetRecord.ordinal.asc())
        ).all()

    assert [(row.asset_id, row.ordinal) for row in rows] == [
        (first.ref.attachment_id, 0),
        (second.ref.attachment_id, 1),
    ]


def test_record_analysis_is_atomic_when_one_input_asset_is_missing(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    asset_repository = AssetRepository(session_factory)
    store = AttachmentStore(tmp_path / "artifacts", asset_repository=asset_repository)

    with store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
    ):
        source = store.save_image_bytes(
            content=b"source-image",
            mime_type="image/png",
            filename="source.png",
            kind="user_upload",
        )

    repository = AnalysisRepository(session_factory)
    analysis_id = repository.record_analysis(
        tool_name="get_room_detail_details_from_photo",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis",
        run_id=None,
        input_asset_id=source.ref.attachment_id,
        input_asset_ids=[source.ref.attachment_id, "missing-asset"],
        request_json={"images": [source.ref.attachment_id, "missing-asset"]},
        result_json={"room_type": "unknown"},
        detections=[],
    )

    assert analysis_id is None

    with session_factory() as session:
        analysis_rows = session.execute(select(AnalysisRunRecord.analysis_id)).all()
        input_rows = session.execute(select(AnalysisInputAssetRecord.analysis_input_asset_id)).all()

    assert analysis_rows == []
    assert input_rows == []


def test_record_analysis_accepts_new_thread_for_same_room_assets(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    asset_repository = AssetRepository(session_factory)
    store = AttachmentStore(tmp_path / "artifacts", asset_repository=asset_repository)

    with store.bind_context(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis-source",
        run_id=None,
    ):
        source = store.save_image_bytes(
            content=b"source-image",
            mime_type="image/png",
            filename="source.png",
            kind="user_upload",
        )

    repository = AnalysisRepository(session_factory)
    analysis_id = repository.record_analysis(
        tool_name="detect_objects_in_image",
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-analysis-followup",
        run_id=None,
        input_asset_id=source.ref.attachment_id,
        request_json={"image": {"attachment_id": source.ref.attachment_id}},
        result_json={"detections": []},
        detections=[],
    )

    assert analysis_id is not None

    with session_factory() as session:
        row = session.execute(
            select(AnalysisRunRecord.room_id, AnalysisRunRecord.thread_id).where(
                AnalysisRunRecord.analysis_id == analysis_id
            )
        ).one()

    assert row.room_id == DEFAULT_DEV_ROOM_ID
    assert row.thread_id == "thread-analysis-followup"
