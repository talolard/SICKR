"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import gettempdir

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from ikea_agent.chat.agent import build_chat_agent
from ikea_agent.chat.graph import ChatGraphDeps
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def create_app(
    runtime: ChatRuntime | None = None,
    *,
    mount_web_ui: bool = True,
    mount_ag_ui: bool = True,
) -> FastAPI:
    """Create FastAPI app and mount the pydantic-ai web chat UI."""

    app = FastAPI(title="ikea_agent chat runtime", version="0.1.0")
    chat_runtime = build_chat_runtime() if runtime is None else runtime
    deps = ChatGraphDeps(runtime=chat_runtime)
    web_agent = build_chat_agent()
    attachment_store = AttachmentStore(
        Path(gettempdir()) / "ikea_agent" / "chat_attachments"
    )

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

    if mount_ag_ui:
        app.mount("/ag-ui", web_agent.to_ag_ui(deps=deps))

    if mount_web_ui:
        app.mount("/", web_agent.to_web(deps=deps))

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="ikea_agent chat runtime (placeholder)")
