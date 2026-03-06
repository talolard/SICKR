from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import (
    AnalysisDetectionRecord,
    AnalysisRunRecord,
    ensure_persistence_schema,
)
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
from ikea_agent.tools.image_analysis.models import DetectedObject


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_duckdb_engine(str(tmp_path / "analysis_repository_test.duckdb"))
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_record_analysis_persists_run_and_detection_rows(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    asset_repository = AssetRepository(session_factory)
    store = AttachmentStore(tmp_path / "artifacts", asset_repository=asset_repository)

    with store.bind_context(thread_id="thread-analysis", run_id=None):
        source = store.save_image_bytes(
            content=b"source-image",
            mime_type="image/png",
            filename="source.png",
            kind="user_upload",
        )

    repository = AnalysisRepository(session_factory)
    analysis_id = repository.record_analysis(
        tool_name="detect_objects_in_image",
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

    assert analysis_row.thread_id == "thread-analysis"
    assert analysis_row.input_asset_id == source.ref.attachment_id
    assert analysis_row.tool_name == "detect_objects_in_image"
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
        thread_id="thread-analysis",
        run_id=None,
        input_asset_id="missing-asset",
        request_json={"image": {"attachment_id": "missing-asset"}},
        result_json={"depth_image": None},
        detections=[],
    )

    assert analysis_id is None
