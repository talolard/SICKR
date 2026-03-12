"""Thread-scoped data route registration helpers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ikea_agent.chat_app.thread_api_models import (
    AnalysisFeedbackCreateRequest,
    AnalysisFeedbackItem,
    AnalysisListItem,
    AssetListItem,
    DetectionListItem,
    FloorPlanRevisionListItem,
    Room3DAssetCreateRequest,
    Room3DAssetListItem,
    Room3DSnapshotCreateRequest,
    Room3DSnapshotListItem,
    ThreadDetailItem,
    ThreadListItem,
    ThreadTitleUpdateRequest,
)
from ikea_agent.persistence.room_3d_repository import Room3DRepository
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository
from ikea_agent.shared.types import BundleProposalToolResult


def _register_thread_data_routes(  # noqa: C901
    app: FastAPI,
    *,
    thread_query_repository: ThreadQueryRepository,
    room_3d_repository: Room3DRepository | None,
) -> None:
    @app.get("/api/threads", response_model=list[ThreadListItem])
    async def list_threads() -> list[ThreadListItem]:
        return thread_query_repository.list_threads()

    @app.get("/api/threads/{thread_id}", response_model=ThreadDetailItem)
    async def get_thread(thread_id: str) -> ThreadDetailItem:
        item = thread_query_repository.get_thread(thread_id=thread_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return item

    @app.patch("/api/threads/{thread_id}/title", response_model=ThreadDetailItem)
    async def update_thread_title(
        thread_id: str,
        payload: ThreadTitleUpdateRequest,
    ) -> ThreadDetailItem:
        item = thread_query_repository.update_thread_title(
            thread_id=thread_id,
            title=payload.title,
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return item

    @app.get("/api/threads/{thread_id}/assets", response_model=list[AssetListItem])
    async def list_thread_assets(thread_id: str) -> list[AssetListItem]:
        return thread_query_repository.list_assets(thread_id=thread_id)

    @app.get(
        "/api/threads/{thread_id}/floor-plan-revisions",
        response_model=list[FloorPlanRevisionListItem],
    )
    async def list_thread_floor_plan_revisions(thread_id: str) -> list[FloorPlanRevisionListItem]:
        return thread_query_repository.list_floor_plan_revisions(thread_id=thread_id)

    @app.get("/api/threads/{thread_id}/analyses", response_model=list[AnalysisListItem])
    async def list_thread_analyses(thread_id: str) -> list[AnalysisListItem]:
        return thread_query_repository.list_analyses(thread_id=thread_id)

    @app.get(
        "/api/threads/{thread_id}/bundle-proposals",
        response_model=list[BundleProposalToolResult],
    )
    async def list_thread_bundle_proposals(thread_id: str) -> list[BundleProposalToolResult]:
        return thread_query_repository.list_bundle_proposals(thread_id=thread_id)

    @app.get(
        "/api/threads/{thread_id}/analyses/{analysis_id}/feedback",
        response_model=list[AnalysisFeedbackItem],
    )
    async def list_analysis_feedback(
        thread_id: str,
        analysis_id: str,
    ) -> list[AnalysisFeedbackItem]:
        return thread_query_repository.list_analysis_feedback(
            thread_id=thread_id,
            analysis_id=analysis_id,
        )

    @app.post(
        "/api/threads/{thread_id}/analyses/{analysis_id}/feedback",
        response_model=AnalysisFeedbackItem,
    )
    async def create_analysis_feedback(
        thread_id: str,
        analysis_id: str,
        payload: AnalysisFeedbackCreateRequest,
    ) -> AnalysisFeedbackItem:
        created = thread_query_repository.create_analysis_feedback(
            thread_id=thread_id,
            analysis_id=analysis_id,
            feedback_kind=payload.feedback_kind,
            mask_ordinal=payload.mask_ordinal,
            mask_label=payload.mask_label,
            query_text=payload.query_text,
            note=payload.note,
            run_id=payload.run_id,
        )
        if created is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        return created

    @app.get(
        "/api/threads/{thread_id}/images/{asset_id}/detections",
        response_model=list[DetectionListItem],
    )
    async def list_thread_detections_for_image(
        thread_id: str,
        asset_id: str,
    ) -> list[DetectionListItem]:
        return thread_query_repository.list_detections_for_image(
            thread_id=thread_id,
            input_asset_id=asset_id,
        )

    @app.get(
        "/api/threads/{thread_id}/room-3d-assets",
        response_model=list[Room3DAssetListItem],
    )
    async def list_thread_room_3d_assets(thread_id: str) -> list[Room3DAssetListItem]:
        if room_3d_repository is None:
            return []
        return [
            Room3DAssetListItem(
                room_3d_asset_id=item.room_3d_asset_id,
                thread_id=item.thread_id,
                run_id=item.run_id,
                source_asset_id=item.source_asset_id,
                usd_format=item.usd_format,
                metadata=item.metadata,
                created_at=item.created_at,
            )
            for item in room_3d_repository.list_room_3d_assets(thread_id=thread_id)
        ]

    @app.post(
        "/api/threads/{thread_id}/room-3d-assets",
        response_model=Room3DAssetListItem,
    )
    async def create_thread_room_3d_asset(
        thread_id: str,
        payload: Room3DAssetCreateRequest,
    ) -> Room3DAssetListItem:
        if room_3d_repository is None:
            raise HTTPException(status_code=503, detail="room_3d persistence is unavailable")
        created = room_3d_repository.create_room_3d_asset(
            thread_id=thread_id,
            source_asset_id=payload.source_asset_id,
            usd_format=payload.usd_format,
            metadata=payload.metadata,
            run_id=payload.run_id,
        )
        return Room3DAssetListItem(
            room_3d_asset_id=created.room_3d_asset_id,
            thread_id=created.thread_id,
            run_id=created.run_id,
            source_asset_id=created.source_asset_id,
            usd_format=created.usd_format,
            metadata=created.metadata,
            created_at=created.created_at,
        )

    @app.get(
        "/api/threads/{thread_id}/room-3d-snapshots",
        response_model=list[Room3DSnapshotListItem],
    )
    async def list_thread_room_3d_snapshots(thread_id: str) -> list[Room3DSnapshotListItem]:
        if room_3d_repository is None:
            return []
        return [
            Room3DSnapshotListItem(
                room_3d_snapshot_id=item.room_3d_snapshot_id,
                thread_id=item.thread_id,
                run_id=item.run_id,
                snapshot_asset_id=item.snapshot_asset_id,
                room_3d_asset_id=item.room_3d_asset_id,
                camera=item.camera,
                lighting=item.lighting,
                comment=item.comment,
                created_at=item.created_at,
            )
            for item in room_3d_repository.list_room_3d_snapshots(thread_id=thread_id)
        ]

    @app.post(
        "/api/threads/{thread_id}/room-3d-snapshots",
        response_model=Room3DSnapshotListItem,
    )
    async def create_thread_room_3d_snapshot(
        thread_id: str,
        payload: Room3DSnapshotCreateRequest,
    ) -> Room3DSnapshotListItem:
        if room_3d_repository is None:
            raise HTTPException(status_code=503, detail="room_3d persistence is unavailable")
        created = room_3d_repository.create_room_3d_snapshot(
            thread_id=thread_id,
            snapshot_asset_id=payload.snapshot_asset_id,
            room_3d_asset_id=payload.room_3d_asset_id,
            camera=payload.camera,
            lighting=payload.lighting,
            comment=payload.comment,
            run_id=payload.run_id,
        )
        return Room3DSnapshotListItem(
            room_3d_snapshot_id=created.room_3d_snapshot_id,
            thread_id=created.thread_id,
            run_id=created.run_id,
            snapshot_asset_id=created.snapshot_asset_id,
            room_3d_asset_id=created.room_3d_asset_id,
            camera=created.camera,
            lighting=created.lighting,
            comment=created.comment,
            created_at=created.created_at,
        )
