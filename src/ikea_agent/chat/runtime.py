"""Runtime wiring for chat graph dependencies."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.retrieval.catalog_repository import CatalogRepository
from ikea_agent.retrieval.reranker import Reranker, RerankerBackend, get_reranker
from ikea_agent.shared.sqlalchemy_db import (
    create_database_engine,
    create_session_factory,
    resolve_database_url,
)
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
    sqlalchemy_engine: Engine
    session_factory: sessionmaker[Session]
    embedder: Embedder
    catalog_repository: CatalogRepository
    reranker: Reranker


async def embed_query(runtime: ChatRuntime, query_text: str) -> tuple[float, ...]:
    """Embed one query string with configured provider and dimensions."""

    response = await runtime.embedder.embed_query(query_text)
    if not response.embeddings:
        return ()
    return tuple(float(value) for value in response.embeddings[0])


async def embed_queries(
    runtime: ChatRuntime, query_texts: Sequence[str]
) -> list[tuple[float, ...]]:
    """Embed one or more query strings in batches using the configured provider."""

    normalized_queries = [query.strip() for query in query_texts]
    if not normalized_queries:
        return []

    vectors: list[tuple[float, ...]] = []
    batch_size = runtime.settings.embedding_query_batch_size
    for start_index in range(0, len(normalized_queries), batch_size):
        batch = normalized_queries[start_index : start_index + batch_size]
        response = await runtime.embedder.embed_query(batch)
        embeddings = response.embeddings or []
        for index, _query_text in enumerate(batch):
            if index >= len(embeddings):
                vectors.append(())
                continue
            vectors.append(tuple(float(value) for value in embeddings[index]))
    return vectors


def search_catalog(
    runtime: ChatRuntime,
    *,
    query_vector: tuple[float, ...],
    filters: RetrievalFilters,
    result_limit: int,
) -> list[RetrievalResult]:
    """Run the active semantic retrieval query directly in Postgres."""

    return runtime.catalog_repository.search_semantic_products(
        query_vector=query_vector,
        embedding_model=runtime.settings.gemini_model,
        filters=filters,
        result_limit=result_limit,
    )


def resolve_reranker_backend(settings: AppSettings) -> RerankerBackend:
    """Resolve the one supported reranker backend story for current settings."""

    if not settings.rerank_enabled:
        return "identity"
    return settings.rerank_backend


def build_chat_runtime() -> ChatRuntime:
    """Build chat runtime with Postgres-backed retrieval dependencies."""

    settings = get_settings()
    database_url = resolve_database_url(database_url=settings.database_url)
    sqlalchemy_engine = create_database_engine(
        database_url,
        pool_mode=settings.database_pool_mode,
    )
    session_factory = create_session_factory(sqlalchemy_engine)

    embedding_settings = build_google_embedding_settings(dimensions=settings.embedding_dimensions)
    embedder = Embedder(
        settings.embedding_model_uri,
        settings=embedding_settings,
    )

    backend = resolve_reranker_backend(settings)

    return ChatRuntime(
        settings=settings,
        sqlalchemy_engine=sqlalchemy_engine,
        session_factory=session_factory,
        embedder=embedder,
        catalog_repository=CatalogRepository(sqlalchemy_engine),
        reranker=get_reranker(backend, settings),
    )
