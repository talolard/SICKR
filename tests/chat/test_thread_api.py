from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app
from ikea_agent.persistence.models import (
    AgentRunRecord,
    AnalysisDetectionRecord,
    AnalysisRunRecord,
    AssetRecord,
    FloorPlanRevisionRecord,
    SearchResultRecord,
    SearchRunRecord,
    ThreadRecord,
    ensure_persistence_schema,
)
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine


@dataclass
class _RuntimeStub:
    sqlalchemy_engine: object
    session_factory: sessionmaker[Session]


def _runtime(tmp_path: Path) -> _RuntimeStub:
    engine = create_duckdb_engine(str(tmp_path / "thread_api_test.duckdb"))
    ensure_persistence_schema(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _RuntimeStub(sqlalchemy_engine=engine, session_factory=session_factory)


def _seed(runtime: _RuntimeStub, *, tmp_path: Path) -> None:
    now = datetime.now(UTC)
    with runtime.session_factory() as session:
        session.add(
            ThreadRecord(
                thread_id="thread-api",
                owner_id=None,
                title="Initial title",
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
            AssetRecord(
                asset_id="asset-api",
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
                thread_id="thread-api",
                run_id="run-api",
                tool_name="detect_objects_in_image",
                input_asset_id="asset-api",
                request_json="{}",
                result_json="{}",
                created_at=now,
            )
        )
        session.flush()
        session.add(
            AnalysisDetectionRecord(
                analysis_detection_id="det-api",
                analysis_id="analysis-api",
                ordinal=1,
                label="chair",
                bbox_x1_px=1,
                bbox_y1_px=2,
                bbox_x2_px=3,
                bbox_y2_px=4,
                bbox_x1_norm=0.1,
                bbox_y1_norm=0.2,
                bbox_x2_norm=0.3,
                bbox_y2_norm=0.4,
            )
        )
        session.add(
            SearchRunRecord(
                search_id="search-api",
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
            SearchResultRecord(
                search_result_id="search-res-api",
                search_id="search-api",
                rank=1,
                product_id="prod-1",
                product_name="PAX",
                product_type="wardrobe",
                main_category="storage",
                sub_category="wardrobes",
                width_cm=80.0,
                depth_cm=60.0,
                height_cm=200.0,
                price_eur=199.0,
            )
        )
        session.commit()


def test_thread_data_routes_return_thread_scoped_records(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _seed(runtime, tmp_path=tmp_path)
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", runtime),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    list_response = client.get("/api/threads")
    detail_response = client.get("/api/threads/thread-api")
    title_response = client.patch("/api/threads/thread-api/title", json={"title": "Updated"})
    assets_response = client.get("/api/threads/thread-api/assets")
    revisions_response = client.get("/api/threads/thread-api/floor-plan-revisions")
    analyses_response = client.get("/api/threads/thread-api/analyses")
    detections_response = client.get("/api/threads/thread-api/images/asset-api/detections")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert title_response.status_code == 200
    assert assets_response.status_code == 200
    assert revisions_response.status_code == 200
    assert analyses_response.status_code == 200
    assert detections_response.status_code == 200

    assert list_response.json()[0]["thread_id"] == "thread-api"
    assert detail_response.json()["asset_count"] == 1
    assert title_response.json()["title"] == "Updated"
    assert assets_response.json()[0]["asset_id"] == "asset-api"
    assert revisions_response.json()[0]["floor_plan_revision_id"] == "fprev-api"
    assert analyses_response.json()[0]["analysis_id"] == "analysis-api"
    assert detections_response.json()[0]["analysis_detection_id"] == "det-api"
