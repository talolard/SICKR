"""Runtime wiring for chat graph dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import duckdb
from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.retrieval.catalog_repository import CatalogRepository
from ikea_agent.retrieval.reranker import Reranker, RerankerBackend, get_reranker
from ikea_agent.retrieval.service import MilvusAccessService, VectorMatch
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db import connect_db
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult

GoogleEmbeddingTaskType = Literal[
    "TASK_TYPE_UNSPECIFIED",
    "RETRIEVAL_QUERY",
    "RETRIEVAL_DOCUMENT",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
    "QUESTION_ANSWERING",
    "FACT_VERIFICATION",
]


try:
    from pydantic_ai.embeddings.google import GoogleEmbeddingSettings
except ImportError:

    class GoogleEmbeddingSettings(EmbeddingSettings, total=False):
        """Google embedding-specific runtime settings."""

        google_task_type: GoogleEmbeddingTaskType


def build_google_embedding_settings(*, dimensions: int) -> GoogleEmbeddingSettings:
    """Build Google embedding settings optimized for retrieval queries."""

    return GoogleEmbeddingSettings(
        dimensions=dimensions,
        google_task_type="RETRIEVAL_QUERY",
    )


@dataclass(frozen=True, slots=True)
class ChatRuntime:
    """Container with initialized runtime dependencies for chat execution."""

    settings: AppSettings
    connection: duckdb.DuckDBPyConnection
    embedder: Embedder
    milvus_service: MilvusAccessService
    catalog_repository: CatalogRepository
    reranker: Reranker


async def embed_query(runtime: ChatRuntime, query_text: str) -> tuple[float, ...]:
    """Embed one query string with configured provider and dimensions."""

    response = await runtime.embedder.embed_query(query_text)
    if not response.embeddings:
        return ()
    return tuple(float(value) for value in response.embeddings[0])


def search_candidates(
    runtime: ChatRuntime,
    *,
    query_vector: tuple[float, ...],
    filters: RetrievalFilters,
    result_limit: int,
) -> list[RetrievalResult]:
    """Run Milvus search then hydrate typed product rows from DuckDB."""

    candidate_limit = max(result_limit * 10, runtime.settings.retrieval_candidate_limit)
    candidates: list[VectorMatch] = runtime.milvus_service.search(
        query_vector=query_vector,
        embedding_model=runtime.settings.gemini_model,
        candidate_limit=candidate_limit,
    )
    return runtime.catalog_repository.hydrate_candidates(
        candidates=candidates,
        filters=filters,
        result_limit=result_limit,
    )


def build_chat_runtime() -> ChatRuntime:
    """Build chat runtime with schema bootstrap and service dependencies."""

    settings = get_settings()
    connection = connect_db(settings.duckdb_path)
    ensure_runtime_schema(connection)

    embedding_settings = build_google_embedding_settings(dimensions=settings.embedding_dimensions)
    embedder = Embedder(
        settings.embedding_model_uri,
        settings=embedding_settings,
    )
    milvus_service = MilvusAccessService(settings)
    milvus_service.ensure_collection()

    backend: RerankerBackend
    if not settings.rerank_enabled:
        backend = "identity"
    elif settings.rerank_backend == "lexical":
        backend = "lexical"
    else:
        backend = "transformer"

    return ChatRuntime(
        settings=settings,
        connection=connection,
        embedder=embedder,
        milvus_service=milvus_service,
        catalog_repository=CatalogRepository(connection),
        reranker=get_reranker(backend, settings),
    )
