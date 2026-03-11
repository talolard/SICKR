"""Runtime wiring for chat graph dependencies."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from logging import getLogger
from typing import Literal, Protocol

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.retrieval.catalog_repository import (
    CatalogRepository,
    EmbeddingSnapshotRepository,
)
from ikea_agent.retrieval.reranker import Reranker, RerankerBackend, get_reranker
from ikea_agent.retrieval.service import MilvusAccessService, VectorMatch
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine, create_session_factory
from ikea_agent.shared.types import RetrievalFilters, RetrievalResult

logger = getLogger(__name__)

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


class EmbeddingRowsRepository(Protocol):
    """Minimal surface needed to load persisted embeddings for Milvus hydration."""

    def read_embedding_rows(
        self, *, embedding_model: str
    ) -> list[tuple[str, str, tuple[float, ...]]]:
        """Return embedding rows keyed by sku and embedding model."""


class MilvusHydrationService(Protocol):
    """Minimal surface needed to hydrate Milvus from persisted embeddings."""

    def row_count(self) -> int:
        """Return current row count for the active collection."""

    def upsert_rows(self, rows: list[tuple[str, str, tuple[float, ...]]]) -> None:
        """Upsert embedding rows into the active collection."""


def sync_milvus_from_snapshot_if_empty(
    *,
    repository: EmbeddingRowsRepository,
    milvus_service: MilvusHydrationService,
    embedding_model: str,
) -> int:
    """Hydrate Milvus from DuckDB embeddings when collection has no vectors."""

    if milvus_service.row_count() > 0:
        return 0

    rows = repository.read_embedding_rows(embedding_model=embedding_model)
    milvus_service.upsert_rows(rows)
    logger.info("milvus_hydrated_from_snapshot", extra={"row_count": len(rows)})
    return len(rows)


@dataclass(frozen=True, slots=True)
class ChatRuntime:
    """Container with initialized runtime dependencies for chat execution."""

    settings: AppSettings
    sqlalchemy_engine: Engine
    session_factory: sessionmaker[Session]
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
    sqlalchemy_engine = create_duckdb_engine(settings.duckdb_path)
    session_factory = create_session_factory(sqlalchemy_engine)
    ensure_runtime_schema(sqlalchemy_engine)
    snapshot_repository = EmbeddingSnapshotRepository(sqlalchemy_engine)

    embedding_settings = build_google_embedding_settings(dimensions=settings.embedding_dimensions)
    embedder = Embedder(
        settings.embedding_model_uri,
        settings=embedding_settings,
    )
    milvus_service = MilvusAccessService(settings)
    milvus_service.ensure_collection()
    sync_milvus_from_snapshot_if_empty(
        repository=snapshot_repository,
        milvus_service=milvus_service,
        embedding_model=settings.gemini_model,
    )

    backend: RerankerBackend
    if not settings.rerank_enabled:
        backend = "identity"
    elif settings.rerank_backend == "lexical":
        backend = "lexical"
    else:
        backend = "transformer"

    return ChatRuntime(
        settings=settings,
        sqlalchemy_engine=sqlalchemy_engine,
        session_factory=session_factory,
        embedder=embedder,
        milvus_service=milvus_service,
        catalog_repository=CatalogRepository(sqlalchemy_engine),
        reranker=get_reranker(backend, settings),
    )
