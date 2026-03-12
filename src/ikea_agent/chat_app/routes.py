"""Route registration helpers for uploads, diagnostics, and generated artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict
from logging import getLogger
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from ikea_agent.chat.agents.index import (
    AgentCatalogItem,
    AgentDescription,
    describe_agent,
    list_agent_catalog,
)
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat_app.comment_bundles import (
    DEFAULT_COMMENT_TITLE,
    CommentBundleInput,
    CommentBundleWriter,
    FeedbackImageInput,
)
from ikea_agent.chat_app.openusd_ingest import (
    OpenUsdValidationError,
    inspect_openusd_bytes,
)
from ikea_agent.chat_app.thread_api_models import (
    CommentBundleCreateRequest,
    CommentBundleCreateResponse,
    RecentTraceReportItem,
    RecentTraceReportListResponse,
    TraceReportCreateRequest,
    TraceReportCreateResponse,
)
from ikea_agent.chat_app.trace_reports import TraceReportInput, TraceReportWriter
from ikea_agent.integrations.beads_cli import BeadsTraceIssueCreator
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.room_3d_repository import Room3DRepository
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    ThreadRunHistoryEntry,
)
from ikea_agent.shared.types import ImageToolOutput

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
logger = getLogger(__name__)


def _build_attachment_store(
    *,
    root_dir: Path,
    asset_repository: AssetRepository | None,
) -> AttachmentStore:
    return AttachmentStore(root_dir=root_dir, asset_repository=asset_repository)


def _register_attachment_routes(app: FastAPI, attachment_store: AttachmentStore) -> None:
    @app.post("/attachments")
    async def upload_attachment(request: Request) -> dict[str, object]:
        """Upload one image and return a typed attachment reference."""

        mime_type = request.headers.get("content-type", "")
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Unsupported attachment type. Use png/jpeg/webp images.",
            )

        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Attachment is empty.")
        if len(body) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Attachment exceeds 10MB upload limit.",
            )

        stored = attachment_store.save_image_bytes(
            content=body,
            mime_type=mime_type,
            filename=request.headers.get("x-filename"),
            thread_id=request.headers.get("x-thread-id") or None,
            run_id=request.headers.get("x-run-id") or None,
            kind="user_upload",
        )
        return asdict(stored.ref)

    @app.get("/attachments/{attachment_id}")
    async def get_attachment(attachment_id: str) -> FileResponse:
        """Serve one previously uploaded attachment by id."""

        stored = attachment_store.resolve(attachment_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Attachment not found.")
        return FileResponse(
            path=stored.path,
            media_type=stored.ref.mime_type,
            filename=stored.ref.file_name,
        )


def _resolve_feedback_images(
    *,
    attachment_store: AttachmentStore,
    attachment_ids: list[str],
) -> list[FeedbackImageInput]:
    images: list[FeedbackImageInput] = []
    for attachment_id in attachment_ids:
        stored = attachment_store.resolve(attachment_id)
        if stored is None:
            continue
        content = stored.path.read_bytes()
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Feedback image exceeds 10MB upload limit.",
            )
        images.append(
            FeedbackImageInput(
                file_name=stored.ref.file_name or f"{attachment_id}.bin",
                mime_type=stored.ref.mime_type,
                content=content,
            )
        )
    return images


def _build_feedback_history_payloads(
    *,
    run_history_repository: RunHistoryRepository | None,
    thread_id: str | None,
) -> tuple[str | None, str | None]:
    if run_history_repository is None or not thread_id:
        return None, None
    history: list[ThreadRunHistoryEntry] = run_history_repository.list_thread_run_history(
        thread_id=thread_id,
        limit=250,
    )
    user_prompts = [
        entry.user_prompt_text for entry in history if entry.user_prompt_text is not None
    ]
    user_prompt_history_json = json.dumps(user_prompts, ensure_ascii=True)
    full_message_history_json = json.dumps(
        [
            {
                "run_id": entry.run_id,
                "parent_run_id": entry.parent_run_id,
                "status": entry.status,
                "user_prompt_text": entry.user_prompt_text,
                "started_at": entry.started_at,
                "ended_at": entry.ended_at,
                "agui_input_messages_json": entry.agui_input_messages_json,
                "pydantic_all_messages_json": entry.pydantic_all_messages_json,
                "pydantic_new_messages_json": entry.pydantic_new_messages_json,
            }
            for entry in history
        ],
        ensure_ascii=True,
    )
    return user_prompt_history_json, full_message_history_json


def _register_comment_routes(
    app: FastAPI,
    *,
    feedback_enabled: bool,
    feedback_writer: CommentBundleWriter,
    attachment_store: AttachmentStore,
    run_history_repository: RunHistoryRepository | None,
) -> None:
    @app.post("/api/comments", response_model=CommentBundleCreateResponse)
    async def create_comment_bundle(
        payload: CommentBundleCreateRequest,
    ) -> CommentBundleCreateResponse:
        """Persist one UI feedback bundle to the local comments directory."""

        if not feedback_enabled:
            raise HTTPException(
                status_code=503,
                detail="Feedback capture is disabled. Enable FEEDBACK_CAPTURE_ENABLED.",
            )

        images = _resolve_feedback_images(
            attachment_store=attachment_store,
            attachment_ids=payload.attachment_ids,
        )

        normalized_title = (payload.title or "").strip() or DEFAULT_COMMENT_TITLE
        normalized_comment = payload.comment.strip()
        if (
            normalized_title == DEFAULT_COMMENT_TITLE
            and not normalized_comment
            and len(images) == 0
        ):
            raise HTTPException(
                status_code=422,
                detail="Feedback must include a comment, images, or a non-default title.",
            )

        user_prompt_history_json, full_message_history_json = _build_feedback_history_payloads(
            run_history_repository=run_history_repository,
            thread_id=payload.thread_id,
        )

        bundle_payload = CommentBundleInput(
            title=normalized_title,
            comment=normalized_comment,
            page_url=payload.page_url,
            thread_id=payload.thread_id,
            user_agent=payload.user_agent,
            include_console_log=payload.include_console_log,
            include_dom_snapshot=payload.include_dom_snapshot,
            include_ui_state=payload.include_ui_state,
            console_log_json=payload.console_log,
            dom_snapshot_html=payload.dom_snapshot,
            ui_state_json=payload.ui_state,
            user_input_history_json=user_prompt_history_json,
            full_message_history_json=full_message_history_json,
            images=images,
        )
        try:
            result = feedback_writer.write_bundle(bundle_payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="Feedback payload contains invalid JSON artifact content.",
            ) from exc

        return CommentBundleCreateResponse(
            comment_id=result.comment_id,
            directory=result.directory,
            markdown_path=result.markdown_path,
            saved_images_count=result.saved_images_count,
        )


def _register_trace_routes(
    app: FastAPI,
    *,
    trace_writer: TraceReportWriter,
    beads_creator: BeadsTraceIssueCreator,
    run_history_repository: RunHistoryRepository,
) -> None:
    @app.get("/api/traces/recent", response_model=RecentTraceReportListResponse)
    async def list_recent_trace_reports(limit: int = 5) -> RecentTraceReportListResponse:
        """Return recent saved trace bundles for diagnostics surfaces."""

        recent = trace_writer.list_recent(limit=min(max(limit, 1), 20))
        return RecentTraceReportListResponse(
            traces=[
                RecentTraceReportItem(
                    trace_id=item.trace_id,
                    title=item.title,
                    created_at=item.created_at,
                    thread_id=item.thread_id,
                    agent_name=item.agent_name,
                    directory=item.directory,
                    markdown_path=item.markdown_path,
                )
                for item in recent
            ]
        )

    @app.post("/api/traces", response_model=TraceReportCreateResponse)
    async def create_trace_report(payload: TraceReportCreateRequest) -> TraceReportCreateResponse:
        """Persist one current-thread trace report and create Beads triage work."""

        normalized_title = payload.title.strip()
        if not normalized_title:
            raise HTTPException(status_code=422, detail="Trace title must not be blank.")

        history = run_history_repository.list_thread_run_history(
            thread_id=payload.thread_id,
            agent_name=payload.agent_name,
        )
        if not history:
            raise HTTPException(
                status_code=404, detail="No archived runs found for that thread/agent."
            )

        result = trace_writer.write_bundle(
            TraceReportInput(
                title=normalized_title,
                description=payload.description.strip() if payload.description else None,
                page_url=payload.page_url,
                thread_id=payload.thread_id,
                agent_name=payload.agent_name,
                user_agent=payload.user_agent,
                console_log_json=payload.console_log if payload.include_console_log else None,
                run_history=history,
            )
        )

        try:
            beads_result = beads_creator.create_trace_epic_and_task(
                title=normalized_title,
                description=payload.description.strip() if payload.description else None,
                trace_directory=result.directory,
                trace_json_path=result.trace_json_path,
                thread_id=payload.thread_id,
                agent_name=payload.agent_name,
            )
        except Exception:
            logger.exception("trace_report_beads_create_failed")
            return TraceReportCreateResponse(
                trace_id=result.trace_id,
                directory=result.directory,
                trace_json_path=result.trace_json_path,
                markdown_path=result.markdown_path,
                status="saved_without_beads",
            )

        return TraceReportCreateResponse(
            trace_id=result.trace_id,
            directory=result.directory,
            trace_json_path=result.trace_json_path,
            markdown_path=result.markdown_path,
            beads_epic_id=beads_result.epic_id,
            beads_task_id=beads_result.task_id,
            status="saved_and_linked",
        )


def _register_agent_catalog_routes(app: FastAPI) -> None:
    @app.get("/api/agents")
    async def list_agents() -> dict[str, list[AgentCatalogItem]]:
        """Return all registered agents for UI navigation."""

        return {"agents": list_agent_catalog()}

    @app.get("/api/agents/{agent_name}/metadata")
    async def get_agent_metadata(agent_name: str) -> AgentDescription:
        """Return prompt and tool metadata for one agent."""

        try:
            return describe_agent(agent_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


def _floor_plan_preview_svg() -> str:
    # Keep each line short to satisfy lint, and keep output deterministic for caching.
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420">',
        '  <rect x="20" y="20" width="600" height="380" fill="#f6f6f6" stroke="#333" />',
        '  <rect x="80" y="80" width="180" height="120" fill="#d9e6ff" stroke="#1d4ed8" />',
        '  <rect x="340" y="120" width="220" height="160" fill="#ffe4d6" stroke="#c2410c" />',
        '  <text x="90" y="110" font-size="20" fill="#1f2937">Wardrobe</text>',
        '  <text x="350" y="150" font-size="20" fill="#1f2937">Bed</text>',
        "</svg>",
    ]
    return "\n".join(lines)


def _register_generated_image_routes(app: FastAPI, attachment_store: AttachmentStore) -> None:
    @app.post("/generated-images/floor-plan")
    async def generate_floor_plan_image(request: Request) -> dict[str, object]:
        """Generate and store a simple floor plan preview artifact."""

        stored = attachment_store.save_image_bytes(
            content=_floor_plan_preview_svg().encode("utf-8"),
            mime_type="image/svg+xml",
            filename="generated-floor-plan.svg",
            thread_id=request.headers.get("x-thread-id") or None,
            run_id=request.headers.get("x-run-id") or None,
            kind="generated_preview",
        )
        output = ImageToolOutput(
            caption="Draft floor plan preview generated from current room assumptions.",
            images=[stored.ref],
        )
        return asdict(output)


def _register_openusd_routes(
    app: FastAPI,
    *,
    attachment_store: AttachmentStore,
    room_3d_repository: Room3DRepository | None,
) -> None:
    @app.post("/room-3d/openusd-ingest")
    async def ingest_openusd_asset(request: Request) -> dict[str, object]:
        """Validate one OpenUSD upload and persist room 3D asset metadata."""

        filename = request.headers.get("x-filename")
        if not filename:
            raise HTTPException(status_code=400, detail="Missing required header `x-filename`.")
        body = await request.body()
        if len(body) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413,
                detail="OpenUSD upload exceeds 10MB limit.",
            )
        try:
            inspection = inspect_openusd_bytes(content=body, filename=filename)
        except OpenUsdValidationError as exc:
            raise HTTPException(
                status_code=415,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        stored = attachment_store.save_bytes(
            content=body,
            mime_type="model/vnd.usd",
            filename=filename,
            thread_id=request.headers.get("x-thread-id") or None,
            run_id=request.headers.get("x-run-id") or None,
            kind="room_3d_usd",
        )
        if room_3d_repository is None:
            return {
                "room_3d_asset_id": None,
                "source_asset": asdict(stored.ref),
                "usd_format": inspection.usd_format,
                "metadata": inspection.metadata,
            }

        thread_id = request.headers.get("x-thread-id") or "anonymous-thread"
        room_asset = room_3d_repository.create_room_3d_asset(
            thread_id=thread_id,
            source_asset_id=stored.ref.attachment_id,
            usd_format=inspection.usd_format,
            metadata=inspection.metadata,
            run_id=request.headers.get("x-run-id") or None,
        )
        return {
            "room_3d_asset_id": room_asset.room_3d_asset_id,
            "source_asset": asdict(stored.ref),
            "usd_format": room_asset.usd_format,
            "metadata": room_asset.metadata,
        }
