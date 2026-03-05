"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import gettempdir

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from ikea_agent.chat.agent import build_chat_agent
from ikea_agent.chat.deps import ChatAgentDeps, ChatAgentState
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import ImageToolOutput

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _build_attachment_store() -> AttachmentStore:
    return AttachmentStore(Path(gettempdir()) / "ikea_agent" / "chat_attachments")


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
    async def generate_floor_plan_image() -> dict[str, object]:
        """Generate and store a simple floor plan preview artifact."""

        stored = attachment_store.save_image_bytes(
            content=_floor_plan_preview_svg().encode("utf-8"),
            mime_type="image/svg+xml",
            filename="generated-floor-plan.svg",
        )
        output = ImageToolOutput(
            caption="Draft floor plan preview generated from current room assumptions.",
            images=[stored.ref],
        )
        return asdict(output)


def create_app(
    runtime: ChatRuntime | None = None,
    *,
    mount_web_ui: bool = True,
    mount_ag_ui: bool = True,
) -> FastAPI:
    """Create FastAPI app and mount the pydantic-ai web chat UI."""

    app = FastAPI(title="ikea_agent chat runtime", version="0.1.0")
    chat_runtime = build_chat_runtime() if runtime is None else runtime
    web_agent = build_chat_agent()
    attachment_store = _build_attachment_store()
    deps = ChatAgentDeps(
        runtime=chat_runtime,
        attachment_store=attachment_store,
        state=ChatAgentState(),
    )
    _register_attachment_routes(app, attachment_store)
    _register_generated_image_routes(app, attachment_store)

    if mount_ag_ui:
        app.mount("/ag-ui", web_agent.to_ag_ui(deps=deps))

    if mount_web_ui:
        app.mount("/", web_agent.to_web(deps=deps))

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="ikea_agent chat runtime (placeholder)")
