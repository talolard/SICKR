"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

import json
from dataclasses import asdict
from logging import getLogger
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic_ai import Agent
from pydantic_ai.ag_ui import handle_ag_ui_request

from ikea_agent.chat.agent import build_chat_agent
from ikea_agent.chat.deps import ChatAgentDeps, ChatAgentState
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat_app.comment_bundles import (
    CommentBundleInput,
    CommentBundleWriter,
    FeedbackImageInput,
)
from ikea_agent.chat_app.openusd_ingest import (
    OpenUsdValidationError,
    inspect_openusd_bytes,
)
from ikea_agent.chat_app.thread_api_models import (
    AnalysisListItem,
    AssetListItem,
    CommentBundleCreateRequest,
    CommentBundleCreateResponse,
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
from ikea_agent.config import get_settings
from ikea_agent.observability.logfire_setup import configure_logfire, instrument_fastapi_app
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.room_3d_repository import Room3DRepository
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository
from ikea_agent.shared.types import ImageToolOutput
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
logger = getLogger(__name__)


class _ArchivedMessagesResult(Protocol):
    def all_messages_json(self) -> bytes: ...

    def new_messages_json(self) -> bytes: ...


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


def _register_comment_routes(
    app: FastAPI,
    *,
    feedback_enabled: bool,
    feedback_writer: CommentBundleWriter,
    attachment_store: AttachmentStore,
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

        images: list[FeedbackImageInput] = []
        for attachment_id in payload.attachment_ids:
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

        bundle_payload = CommentBundleInput(
            title=payload.title,
            comment=payload.comment,
            page_url=payload.page_url,
            thread_id=payload.thread_id,
            user_agent=payload.user_agent,
            include_console_log=payload.include_console_log,
            include_dom_snapshot=payload.include_dom_snapshot,
            include_ui_state=payload.include_ui_state,
            console_log_json=payload.console_log,
            dom_snapshot_html=payload.dom_snapshot,
            ui_state_json=payload.ui_state,
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


def _register_ag_ui_route(
    app: FastAPI,
    *,
    web_agent: Agent[ChatAgentDeps, str],
    deps: ChatAgentDeps,
    run_history_repository: RunHistoryRepository | None,
) -> None:
    @app.post("/ag-ui")
    @app.post("/ag-ui/")
    async def run_ag_ui(request: Request) -> Response:
        body = await request.body()
        run_id = f"agui-{uuid4().hex[:16]}"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            run_id = str(payload.get("run_id") or run_id)
            thread_id = str(payload.get("thread_id") or "anonymous-thread")
            parent_run_id = payload.get("parent_run_id")
            parent_run_id_value = str(parent_run_id) if isinstance(parent_run_id, str) else None
            message_payload = payload.get("messages")
            messages = message_payload if isinstance(message_payload, list) else []
            user_prompt_text = extract_last_user_prompt(
                [item for item in messages if isinstance(item, dict)]
            )
            if run_history_repository is not None:
                run_history_repository.record_run_start(
                    thread_id=thread_id,
                    run_id=run_id,
                    parent_run_id=parent_run_id_value,
                    user_prompt_text=user_prompt_text,
                    agui_input_messages_json=json.dumps(messages),
                )
            deps.state.thread_id = thread_id
            deps.state.run_id = run_id
        except Exception:
            # If request parsing fails, proceed with AG-UI normal error semantics.
            logger.debug("failed_to_parse_ag_ui_payload_for_run_history", exc_info=True)

        async def _on_complete(result: _ArchivedMessagesResult) -> None:
            if run_history_repository is not None:
                run_history_repository.record_run_complete(
                    run_id=run_id,
                    pydantic_all_messages_json=result.all_messages_json(),
                    pydantic_new_messages_json=result.new_messages_json(),
                )

        try:
            with deps.attachment_store.bind_context(
                thread_id=deps.state.thread_id or "anonymous-thread",
                run_id=deps.state.run_id,
            ):
                return await handle_ag_ui_request(
                    web_agent,
                    request,
                    deps=deps,
                    on_complete=_on_complete,
                )
        except Exception as exc:
            if run_history_repository is not None:
                run_history_repository.record_run_failed(run_id=run_id, error_message=str(exc))
            raise


def create_app(
    runtime: ChatRuntime | None = None,
    *,
    mount_web_ui: bool = True,
    mount_ag_ui: bool = True,
) -> FastAPI:
    """Create FastAPI app and mount the pydantic-ai web chat UI."""

    settings = get_settings()
    configure_logfire(settings)
    app = FastAPI(title="ikea_agent chat runtime", version="0.1.0")
    instrument_fastapi_app(app)
    chat_runtime = build_chat_runtime() if runtime is None else runtime
    if hasattr(chat_runtime, "sqlalchemy_engine"):
        ensure_persistence_schema(chat_runtime.sqlalchemy_engine)
    web_agent = build_chat_agent()
    asset_repository = (
        AssetRepository(chat_runtime.session_factory)
        if hasattr(chat_runtime, "session_factory")
        else None
    )
    attachment_store = _build_attachment_store(
        root_dir=Path(settings.artifact_root_dir),
        asset_repository=asset_repository,
    )
    feedback_writer = CommentBundleWriter(root_dir=Path(settings.feedback_root_dir))
    run_history_repository = (
        RunHistoryRepository(chat_runtime.session_factory)
        if hasattr(chat_runtime, "session_factory")
        else None
    )
    thread_query_repository = (
        ThreadQueryRepository(chat_runtime.session_factory)
        if hasattr(chat_runtime, "session_factory")
        else None
    )
    room_3d_repository = (
        Room3DRepository(chat_runtime.session_factory)
        if hasattr(chat_runtime, "session_factory")
        else None
    )
    deps = ChatAgentDeps(
        runtime=chat_runtime,
        attachment_store=attachment_store,
        floor_plan_scene_store=FloorPlanSceneStore(),
        state=ChatAgentState(),
    )
    _register_attachment_routes(app, attachment_store)
    _register_comment_routes(
        app,
        feedback_enabled=settings.feedback_capture_enabled,
        feedback_writer=feedback_writer,
        attachment_store=attachment_store,
    )
    _register_generated_image_routes(app, attachment_store)
    _register_openusd_routes(
        app,
        attachment_store=attachment_store,
        room_3d_repository=room_3d_repository,
    )
    if thread_query_repository is not None:
        _register_thread_data_routes(
            app,
            thread_query_repository=thread_query_repository,
            room_3d_repository=room_3d_repository,
        )

    if mount_ag_ui:
        _register_ag_ui_route(
            app,
            web_agent=web_agent,
            deps=deps,
            run_history_repository=run_history_repository,
        )

    if mount_web_ui:
        app.mount("/", web_agent.to_web(deps=deps))

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="ikea_agent chat runtime (placeholder)")
