"""High-level retrieval service orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import monotonic
from uuid import uuid4

from ikea_agent.config import get_settings
from ikea_agent.logging_config import get_logger
from ikea_agent.retrieval.embedder import PydanticAIEmbeddingClient
from ikea_agent.retrieval.repository import RetrievalRepository
from ikea_agent.retrieval.vector_store import MilvusLiteVectorStore
from ikea_agent.shared.db import connect_db
from ikea_agent.shared.types import RetrievalRequest, RetrievalResult


@dataclass(frozen=True, slots=True)
class RetrievalExecution:
    """Retrieval response with request metadata for downstream telemetry."""

    request_id: str
    results: list[RetrievalResult]
    latency_ms: int
    low_confidence: bool


class RetrievalService:
    """Semantic retrieval service callable from web and chat graph flows."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._connection = connect_db(settings.duckdb_path)
        self._repository = RetrievalRepository(self._connection)
        self._embedder = PydanticAIEmbeddingClient(settings)
        self._vector_store = MilvusLiteVectorStore(settings)
        self._vector_store.ensure_collection()
        self._sync_milvus_if_needed()
        self._logger = get_logger("retrieval.service")

    async def retrieve(
        self, request: RetrievalRequest, source: str = "web"
    ) -> list[RetrievalResult]:
        """Return ranked products for the given query request."""

        execution = await self.retrieve_with_trace(request=request, source=source)
        return execution.results

    async def retrieve_with_trace(
        self, request: RetrievalRequest, source: str = "web"
    ) -> RetrievalExecution:
        """Return ranked products plus request metadata for request telemetry."""

        start = monotonic()
        query_vector = await self._embedder.embed_query(request.query_text)

        candidate_limit = max(request.result_limit * 10, self._settings.retrieval_candidate_limit)
        candidates = self._vector_store.search(
            query_vector=query_vector,
            embedding_model=self._settings.gemini_model,
            candidate_limit=candidate_limit,
        )
        results = self._repository.hydrate_candidates(
            candidates=candidates,
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
            filters=_filters_for_log(request),
            result_count=len(results),
            latency_ms=latency_ms,
            low_confidence=low_confidence,
        )
        return RetrievalExecution(
            request_id=query_id,
            results=results,
            latency_ms=latency_ms,
            low_confidence=low_confidence,
        )

    def _sync_milvus_if_needed(self) -> None:
        """Populate Milvus collection when empty or configured for forced rebuild."""

        if not self._settings.milvus_rebuild_on_start:
            stats = self._vector_store.search(
                query_vector=tuple(0.0 for _ in range(self._settings.embedding_dimensions)),
                embedding_model=self._settings.gemini_model,
                candidate_limit=1,
            )
            if stats:
                return

        rows = self._repository.read_embedding_rows(embedding_model=self._settings.gemini_model)
        self._vector_store.rebuild(rows)


def _filters_for_log(request: RetrievalRequest) -> dict[str, object]:
    """Return filter payload with only non-null values for structured logs."""

    pruned = _prune_none(asdict(request.filters))
    if isinstance(pruned, dict):
        return pruned
    return {}


def _prune_none(value: object) -> object:
    """Recursively drop `None` fields from nested filter structures."""

    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            pruned_item = _prune_none(item)
            if pruned_item is not None:
                result[key] = pruned_item
        return result if result else None

    if isinstance(value, list):
        result_list = [item for item in (_prune_none(item) for item in value) if item is not None]
        return result_list if result_list else None

    if isinstance(value, tuple):
        result_tuple = tuple(
            item for item in (_prune_none(item) for item in value) if item is not None
        )
        return result_tuple if result_tuple else None

    return value
