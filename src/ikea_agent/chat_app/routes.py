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
from ikea_agent.chat_app.thread_api_models import (
    RecentTraceReportItem,
    RecentTraceReportListResponse,
    TraceReportCreateRequest,
    TraceReportCreateResponse,
)
from ikea_agent.chat_app.trace_reports import TraceReportInput, TraceReportWriter
from ikea_agent.integrations.beads_cli import BeadsTraceIssueCreator
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.run_history_repository import RunHistoryRepository

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


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
                status_code=404,
                detail="No archived runs found for that thread/agent.",
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
