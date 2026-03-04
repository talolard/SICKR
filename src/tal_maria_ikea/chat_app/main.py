"""FastAPI app exposing pydantic-ai web chat and graph-backed JSON API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from tal_maria_ikea.chat.agent import build_chat_agent
from tal_maria_ikea.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from tal_maria_ikea.chat.runtime import ChatRuntime, build_chat_runtime
from tal_maria_ikea.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    QueryExpansionMode,
    RetrievalFilters,
)


class ChatTurnRequest(BaseModel):
    """One chat turn request for API-driven graph execution."""

    query_text: str = Field(min_length=1, max_length=500)
    expansion_mode: QueryExpansionMode = "auto"
    category: str | None = None
    include_keyword: str | None = None
    exclude_keyword: str | None = None
    min_price_eur: float | None = None
    max_price_eur: float | None = None
    width_max_cm: float | None = None


class ChatTurnResponse(BaseModel):
    """Typed API response returned after one graph execution."""

    request_id: str
    conversation_id: str
    answer_text: str
    needs_clarification: bool
    recommended_keys: tuple[str, ...]


class ChatTraceResponse(BaseModel):
    """Minimal persisted trace payload for debugging chat requests."""

    request_id: str
    results: list[dict[str, Any]]
    messages: list[dict[str, Any]]


def create_app(runtime: ChatRuntime | None = None, *, mount_web_ui: bool = True) -> FastAPI:
    """Create configured FastAPI app with mounted web chat and JSON endpoints."""

    app = FastAPI(title="tal_maria_ikea chat runtime", version="0.1.0")
    chat_runtime = build_chat_runtime() if runtime is None else runtime
    graph = build_chat_graph()
    deps = ChatGraphDeps(runtime=chat_runtime)
    app.state.runtime = chat_runtime
    app.state.graph = graph
    app.state.graph_deps = deps

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat/run", response_model=ChatTurnResponse)
    def run_chat(request: ChatTurnRequest) -> ChatTurnResponse:
        filters = _filters_from_request(request)
        result = graph.run_sync(
            ParseUserIntentNode(
                user_message=request.query_text,
                expansion_mode=request.expansion_mode,
                filters=filters,
            ),
            state=ChatGraphState(),
            deps=deps,
        ).output
        return ChatTurnResponse(
            request_id=result.request_id,
            conversation_id=result.conversation_id,
            answer_text=result.answer_text,
            needs_clarification=result.needs_clarification,
            recommended_keys=result.recommended_keys,
        )

    @app.get("/api/chat/trace/{request_id}", response_model=ChatTraceResponse)
    def read_chat_trace(request_id: str) -> ChatTraceResponse:
        phase3_repository = chat_runtime.phase3_repository
        results = phase3_repository.list_results_for_request(request_id=request_id)
        if not results:
            raise HTTPException(status_code=404, detail="request_id not found")

        conversation_id = f"chat-{request_id}"
        messages = phase3_repository.list_conversation_messages(conversation_id=conversation_id)
        return ChatTraceResponse(
            request_id=request_id,
            results=[
                {
                    "canonical_product_key": row.canonical_product_key,
                    "product_name": row.product_name,
                    "semantic_score": row.semantic_score,
                    "price_eur": row.price_eur,
                }
                for row in results
            ],
            messages=[
                {
                    "message_id": row.message_id,
                    "role": row.role,
                    "content_text": row.content_text,
                    "created_at": row.created_at,
                    "prompt_run_id": row.prompt_run_id,
                }
                for row in messages
            ],
        )

    if mount_web_ui:
        web_agent = build_chat_agent()
        app.mount("/chat", web_agent.to_web(deps=deps))

    return app


def _filters_from_request(request: ChatTurnRequest) -> RetrievalFilters:
    return RetrievalFilters(
        category=_optional(request.category),
        include_keyword=_optional(request.include_keyword),
        exclude_keyword=_optional(request.exclude_keyword),
        price=PriceFilterEUR(
            min_eur=request.min_price_eur,
            max_eur=request.max_price_eur,
        ),
        dimensions=DimensionFilter(
            width=DimensionAxisFilter(max_cm=request.width_max_cm),
            depth=DimensionAxisFilter(),
            height=DimensionAxisFilter(),
        ),
    )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


# Avoid network side effects at import time; runserver uses app factory.
app = create_app(mount_web_ui=False)
