"""Runtime wiring for chat graph dependencies and persistence services."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from tal_maria_ikea.config import AppSettings, get_settings
from tal_maria_ikea.phase3.config_repository import ChatConfigRepository
from tal_maria_ikea.phase3.query_expansion import QueryExpansionService
from tal_maria_ikea.phase3.repository import Phase3Repository
from tal_maria_ikea.phase3.reranker import RerankerService
from tal_maria_ikea.phase3.search_summary import SearchSummaryService
from tal_maria_ikea.retrieval.service import RetrievalService
from tal_maria_ikea.shared.db import connect_db, run_sql_file


@dataclass(frozen=True, slots=True)
class ChatRuntime:
    """Container with initialized runtime dependencies for chat execution."""

    settings: AppSettings
    connection: duckdb.DuckDBPyConnection
    retrieval_service: RetrievalService
    expansion_service: QueryExpansionService
    reranker_service: RerankerService
    summary_service: SearchSummaryService
    phase3_repository: Phase3Repository
    config_repository: ChatConfigRepository


def build_chat_runtime() -> ChatRuntime:
    """Build chat runtime with initialized SQL schema and service dependencies."""

    settings = get_settings()
    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/14_market_views.sql")
    run_sql_file(connection, "sql/22_embedding_store.sql")
    run_sql_file(connection, "sql/42_phase3_runtime.sql")
    run_sql_file(connection, "sql/43_chat_config.sql")

    phase3_repository = Phase3Repository(connection)
    config_repository = ChatConfigRepository(connection)
    return ChatRuntime(
        settings=settings,
        connection=connection,
        retrieval_service=RetrievalService(),
        expansion_service=QueryExpansionService(config_repository=config_repository),
        reranker_service=RerankerService(),
        summary_service=SearchSummaryService(
            repository=phase3_repository,
            config_repository=config_repository,
        ),
        phase3_repository=phase3_repository,
        config_repository=config_repository,
    )
