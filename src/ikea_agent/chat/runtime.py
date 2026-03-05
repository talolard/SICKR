"""Runtime wiring for chat graph dependencies."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.retrieval.reranker import RerankerService
from ikea_agent.retrieval.service import RetrievalService
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db import connect_db


@dataclass(frozen=True, slots=True)
class ChatRuntime:
    """Container with initialized runtime dependencies for chat execution."""

    settings: AppSettings
    connection: duckdb.DuckDBPyConnection
    retrieval_service: RetrievalService
    reranker_service: RerankerService


def build_chat_runtime() -> ChatRuntime:
    """Build chat runtime with schema bootstrap and service dependencies."""

    settings = get_settings()
    connection = connect_db(settings.duckdb_path)
    ensure_runtime_schema(connection)

    return ChatRuntime(
        settings=settings,
        connection=connection,
        retrieval_service=RetrievalService(),
        reranker_service=RerankerService(),
    )
