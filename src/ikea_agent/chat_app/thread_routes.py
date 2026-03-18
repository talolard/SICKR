"""Thread-scoped data route registration helpers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ikea_agent.chat_app.thread_api_models import (
    AnalysisFeedbackCreateRequest,
    AnalysisFeedbackItem,
    AssetListItem,
    KnownFactItem,
    ThreadDetailItem,
)
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository
from ikea_agent.shared.types import BundleProposalToolResult


def _register_thread_data_routes(
    app: FastAPI,
    *,
    thread_query_repository: ThreadQueryRepository,
) -> None:
    @app.get("/api/threads/{thread_id}", response_model=ThreadDetailItem)
    async def get_thread(thread_id: str) -> ThreadDetailItem:
        item = thread_query_repository.get_thread(thread_id=thread_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return item

    @app.get("/api/threads/{thread_id}/assets", response_model=list[AssetListItem])
    async def list_thread_assets(thread_id: str) -> list[AssetListItem]:
        return thread_query_repository.list_assets(thread_id=thread_id)

    @app.get(
        "/api/threads/{thread_id}/bundle-proposals",
        response_model=list[BundleProposalToolResult],
    )
    async def list_thread_bundle_proposals(thread_id: str) -> list[BundleProposalToolResult]:
        return thread_query_repository.list_bundle_proposals(thread_id=thread_id)

    @app.get("/api/threads/{thread_id}/known-facts", response_model=list[KnownFactItem])
    async def list_thread_known_facts(thread_id: str) -> list[KnownFactItem]:
        return thread_query_repository.list_known_facts(thread_id=thread_id)

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
