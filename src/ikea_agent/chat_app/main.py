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
from ikea_agent.config import get_settings
from ikea_agent.observability.logfire_setup import configure_logfire, instrument_fastapi_app
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)
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
    run_history_repository = (
        RunHistoryRepository(chat_runtime.session_factory)
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
    _register_generated_image_routes(app, attachment_store)

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
