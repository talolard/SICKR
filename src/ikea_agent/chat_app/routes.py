"""Route registration helpers for uploads, diagnostics, and agent metadata."""

from __future__ import annotations

from dataclasses import asdict
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
from ikea_agent.persistence.asset_repository import AssetRepository

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _build_attachment_store(
    *,
    root_dir: Path,
    asset_repository: AssetRepository | None,
) -> AttachmentStore:
    return AttachmentStore(root_dir=root_dir, asset_repository=asset_repository)


def _resolve_attachment_context(
    request: Request,
    *,
    attachment_store: AttachmentStore,
) -> tuple[str | None, str | None]:
    room_id = request.headers.get("x-room-id") or None
    thread_id = request.headers.get("x-thread-id") or None
    if attachment_store.requires_persistence_context and (room_id is None or thread_id is None):
        raise HTTPException(
            status_code=400,
            detail="Attachment uploads require explicit x-room-id and x-thread-id headers.",
        )
    return room_id, thread_id


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

        room_id, thread_id = _resolve_attachment_context(
            request,
            attachment_store=attachment_store,
        )

        try:
            stored = attachment_store.save_image_bytes(
                content=body,
                mime_type=mime_type,
                filename=request.headers.get("x-filename"),
                room_id=room_id,
                thread_id=thread_id,
                run_id=request.headers.get("x-run-id") or None,
                kind="user_upload",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
