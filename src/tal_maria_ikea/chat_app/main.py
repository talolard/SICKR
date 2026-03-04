"""FastAPI app exposing only the mounted pydantic-ai web chat UI."""

from __future__ import annotations

from fastapi import FastAPI

from tal_maria_ikea.chat.agent import build_chat_agent
from tal_maria_ikea.chat.graph import ChatGraphDeps
from tal_maria_ikea.chat.runtime import ChatRuntime, build_chat_runtime


def create_app(runtime: ChatRuntime | None = None, *, mount_web_ui: bool = True) -> FastAPI:
    """Create FastAPI app and mount the pydantic-ai web chat UI."""

    app = FastAPI(title="tal_maria_ikea chat runtime", version="0.1.0")
    chat_runtime = build_chat_runtime() if runtime is None else runtime
    deps = ChatGraphDeps(runtime=chat_runtime)

    if mount_web_ui:
        web_agent = build_chat_agent()
        app.mount("/", web_agent.to_web(deps=deps))

    return app


# Import-safe placeholder; `uvicorn ... --factory` uses create_app.
app = FastAPI(title="tal_maria_ikea chat runtime (placeholder)")
