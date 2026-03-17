"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi import FastAPI
from pydantic_ai import Agent
from starlette.types import ASGIApp

from ikea_agent.chat.agents.index import (
    AgentCatalogItem,
    AnyAgentDeps,
    build_agent_ag_ui_agent,
    build_agent_deps,
    list_agent_catalog,
)
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime
from ikea_agent.chat_app.agui import _register_ag_ui_routes
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.chat_app.routes import (
    _build_attachment_store,
    _register_agent_catalog_routes,
    _register_attachment_routes,
    _register_trace_routes,
)
from ikea_agent.chat_app.thread_routes import _register_thread_data_routes
from ikea_agent.chat_app.trace_reports import TraceReportWriter
from ikea_agent.config import get_settings
from ikea_agent.integrations.beads_cli import BeadsTraceIssueCreator
from ikea_agent.observability.logfire_setup import configure_logfire, instrument_fastapi_app
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.run_history_repository import RunHistoryRepository
from ikea_agent.persistence.thread_query_repository import ThreadQueryRepository


def _build_agents(catalog: list[AgentCatalogItem]) -> dict[str, Agent[object, str]]:
    """Build AG-UI agent instances keyed by agent name."""

    return {item["name"]: build_agent_ag_ui_agent(item["name"]) for item in catalog}


def _build_deps_by_agent(
    *,
    catalog: list[AgentCatalogItem],
    runtime: ChatRuntime,
    attachment_store: AttachmentStore,
) -> dict[str, AnyAgentDeps]:
    """Build typed deps per agent name."""

    return {
        item["name"]: build_agent_deps(
            item["name"],
            runtime=runtime,
            attachment_store=attachment_store,
        )
        for item in catalog
    }


def _build_web_apps(
    *,
    catalog: list[AgentCatalogItem],
    agents: dict[str, Agent[object, str]],
    deps_by_agent: dict[str, AnyAgentDeps],
    mount_web_ui: bool,
) -> dict[str, ASGIApp]:
    """Build mounted pydantic-ai web apps keyed by agent name."""

    if not mount_web_ui:
        return {}
    return {
        item["name"]: cast(
            "ASGIApp",
            agents[item["name"]].to_web(deps=deps_by_agent[item["name"]]),
        )
        for item in catalog
    }


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
    asset_repository = (
        AssetRepository(chat_runtime.session_factory)
        if hasattr(chat_runtime, "session_factory")
        else None
    )
    attachment_store = _build_attachment_store(
        root_dir=Path(settings.artifact_root_dir),
        asset_repository=asset_repository,
    )
    trace_writer = TraceReportWriter(root_dir=Path(settings.trace_root_dir))
    beads_creator = BeadsTraceIssueCreator(repo_root=Path.cwd())
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
    _register_attachment_routes(app, attachment_store)
    if settings.trace_capture_enabled and run_history_repository is not None:
        _register_trace_routes(
            app,
            trace_writer=trace_writer,
            beads_creator=beads_creator,
            run_history_repository=run_history_repository,
        )
    _register_agent_catalog_routes(app)
    if thread_query_repository is not None:
        _register_thread_data_routes(
            app,
            thread_query_repository=thread_query_repository,
        )

    catalog = list_agent_catalog()
    agents = _build_agents(catalog)
    deps_by_agent = _build_deps_by_agent(
        catalog=catalog,
        runtime=chat_runtime,
        attachment_store=attachment_store,
    )
    web_apps = _build_web_apps(
        catalog=catalog,
        agents=agents,
        deps_by_agent=deps_by_agent,
        mount_web_ui=mount_web_ui,
    )

    if mount_ag_ui:
        _register_ag_ui_routes(
            app,
            agents=agents,
            deps_by_agent=deps_by_agent,
            run_history_repository=run_history_repository,
        )

    if mount_web_ui:
        for item in catalog:
            agent_mount_path = item["web_path"].rstrip("/")
            app.mount(agent_mount_path, web_apps[item["name"]])

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="ikea_agent chat runtime (placeholder)")
