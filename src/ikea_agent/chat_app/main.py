"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

from fastapi import FastAPI

from ikea_agent.chat.agent import build_chat_agent
from ikea_agent.chat.graph import ChatGraphDeps
from ikea_agent.chat.runtime import ChatRuntime, build_chat_runtime


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

    if mount_ag_ui:
        app.mount("/ag-ui", web_agent.to_ag_ui(deps=deps))

    if mount_web_ui:
        app.mount("/", web_agent.to_web(deps=deps))

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="ikea_agent chat runtime (placeholder)")
