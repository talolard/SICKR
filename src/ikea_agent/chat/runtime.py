"""Runtime wiring for chat graph dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import Literal, Protocol

import duckdb
from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.retrieval.catalog_repository import (
    CatalogRepository,
    EmbeddingSnapshotRepository,
)
from ikea_agent.retrieval.reranker import Reranker, RerankerBackend, get_reranker
from ikea_agent.retrieval.service import MilvusAccessService, VectorMatch
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db import connect_db
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
    snapshot_repository = EmbeddingSnapshotRepository(connection)

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
        connection=connection,
        embedder=embedder,
        milvus_service=milvus_service,
        catalog_repository=CatalogRepository(connection),
        reranker=get_reranker(backend, settings),
    )
