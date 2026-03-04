"""High-level retrieval service orchestration."""

from __future__ import annotations

from time import monotonic
from uuid import uuid4

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.ingest.embedding_client import (
    EmbeddingClientConfig,
    VertexGeminiEmbeddingClient,
)
from tal_maria_ikea.logging_config import get_logger
from tal_maria_ikea.retrieval.repository import RetrievalRepository
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import RetrievalRequest, RetrievalResult


class RetrievalService:
    """Semantic retrieval service callable from web and evaluation flows."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._connection = connect_db(settings.duckdb_path)

        run_sql_file(self._connection, "sql/10_schema.sql")
        run_sql_file(self._connection, "sql/14_market_views.sql")
        run_sql_file(self._connection, "sql/22_embedding_store.sql")
        run_sql_file(self._connection, "sql/42_phase3_runtime.sql")

        self._repository = RetrievalRepository(
            self._connection,
            vector_dimensions=settings.embedding_dimensions,
        )
        self._client = VertexGeminiEmbeddingClient(
            EmbeddingClientConfig(
                project_id=settings.gcp_project_id,
                location=settings.gcp_region,
                model_name=settings.gemini_model,
                api_key=settings.gemini_api_key,
                output_dimensions=settings.embedding_dimensions,
            )
        )
        self._logger = get_logger("retrieval.service")

    def retrieve(self, request: RetrievalRequest, source: str = "web") -> list[RetrievalResult]:
        """Return ranked products for the given query request."""

        start = monotonic()
        query_vector = self._client.embed_query(request.query_text)

        results = self._repository.search(
            query_vector=query_vector,
            embedding_model=self._settings.gemini_model,
            filters=request.filters,
            result_limit=request.result_limit,
        )

        latency_ms = int((monotonic() - start) * 1000)
        low_confidence = len(results) == 0
        if results:
            top_score = results[0].semantic_score
            low_confidence = top_score < self._settings.retrieval_low_confidence_threshold

        query_id = str(uuid4())
        self._repository.log_query(
            query_id=query_id,
            query_text=request.query_text,
            filters=request.filters,
            result_limit=request.result_limit,
            low_confidence=low_confidence,
            latency_ms=latency_ms,
            source=source,
        )

        self._logger.info(
            "query_retrieved",
            query_id=query_id,
            query_text=request.query_text,
            result_count=len(results),
            latency_ms=latency_ms,
            low_confidence=low_confidence,
        )
        return results
