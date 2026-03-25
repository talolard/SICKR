"""Room/thread data route registration helpers."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException

from ikea_agent.chat_app.thread_api_models import (
    AnalysisFeedbackCreateRequest,
    AnalysisFeedbackItem,
    AssetListItem,
    KnownFactItem,
    ThreadCreateRequest,
    ThreadDetailItem,
    ThreadListItem,
    ThreadTranscriptResponse,
)
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository
from ikea_agent.shared.types import BundleProposalToolResult


def _require_found[T](item: T | None, *, detail: str = "Thread not found.") -> T:
    if item is None:
        raise HTTPException(status_code=404, detail=detail)
    return item


def _call_or_404[T](loader: Callable[[], T]) -> T:
    try:
        return loader()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _register_room_thread_collection_routes(
    app: FastAPI,
    *,
    thread_query_repository: ThreadQueryRepository,
) -> None:
    @app.get("/api/rooms/{room_id}/threads", response_model=list[ThreadListItem])
    async def list_room_threads(room_id: str) -> list[ThreadListItem]:
        return _call_or_404(lambda: thread_query_repository.list_threads(room_id=room_id))

    @app.post("/api/rooms/{room_id}/threads", response_model=ThreadListItem, status_code=201)
    async def create_room_thread(
        room_id: str,
        payload: ThreadCreateRequest | None = None,
    ) -> ThreadListItem:
        return _call_or_404(
            lambda: thread_query_repository.create_thread(
                room_id=room_id,
                title=payload.title if payload is not None else None,
            )
        )


def _register_thread_feedback_routes(
    app: FastAPI,
    *,
    thread_query_repository: ThreadQueryRepository,
) -> None:
    @app.post(
        "/api/rooms/{room_id}/threads/{thread_id}/analyses/{analysis_id}/feedback",
        response_model=AnalysisFeedbackItem,
    )
    async def create_analysis_feedback(
        room_id: str,
        thread_id: str,
        analysis_id: str,
        payload: AnalysisFeedbackCreateRequest,
    ) -> AnalysisFeedbackItem:
        return _require_found(
            thread_query_repository.create_analysis_feedback(
                room_id=room_id,
                thread_id=thread_id,
                analysis_id=analysis_id,
                feedback_kind=payload.feedback_kind,
                mask_ordinal=payload.mask_ordinal,
                mask_label=payload.mask_label,
                query_text=payload.query_text,
                note=payload.note,
                run_id=payload.run_id,
            ),
            detail="Analysis not found.",
        )


def _register_thread_data_routes(
    app: FastAPI,
    *,
    thread_query_repository: ThreadQueryRepository,
) -> None:
    _register_room_thread_collection_routes(
        app,
        thread_query_repository=thread_query_repository,
    )

    @app.get("/api/rooms/{room_id}/threads/{thread_id}", response_model=ThreadDetailItem)
    async def get_thread(room_id: str, thread_id: str) -> ThreadDetailItem:
        return _require_found(
            thread_query_repository.get_thread(room_id=room_id, thread_id=thread_id)
        )

    @app.get("/api/rooms/{room_id}/threads/{thread_id}/assets", response_model=list[AssetListItem])
    async def list_thread_assets(room_id: str, thread_id: str) -> list[AssetListItem]:
        return _require_found(
            thread_query_repository.list_assets(room_id=room_id, thread_id=thread_id)
        )

    @app.get(
        "/api/rooms/{room_id}/threads/{thread_id}/bundle-proposals",
        response_model=list[BundleProposalToolResult],
    )
    async def list_thread_bundle_proposals(
        room_id: str,
        thread_id: str,
    ) -> list[BundleProposalToolResult]:
        return _require_found(
            thread_query_repository.list_bundle_proposals(room_id=room_id, thread_id=thread_id)
        )

    @app.get(
        "/api/rooms/{room_id}/threads/{thread_id}/known-facts",
        response_model=list[KnownFactItem],
    )
    async def list_thread_known_facts(room_id: str, thread_id: str) -> list[KnownFactItem]:
        return _require_found(
            thread_query_repository.list_known_facts(room_id=room_id, thread_id=thread_id)
        )

    @app.get(
        "/api/rooms/{room_id}/threads/{thread_id}/messages",
        response_model=ThreadTranscriptResponse,
    )
    async def get_thread_messages(room_id: str, thread_id: str) -> ThreadTranscriptResponse:
        return _require_found(
            thread_query_repository.get_transcript(room_id=room_id, thread_id=thread_id)
        )

    _register_thread_feedback_routes(
        app,
        thread_query_repository=thread_query_repository,
    )
