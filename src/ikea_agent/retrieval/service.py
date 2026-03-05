"""Very light Milvus access service for semantic vector retrieval."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pymilvus import MilvusClient

from ikea_agent.config import AppSettings


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """One vector match from Milvus retrieval."""

    canonical_product_key: str
    semantic_score: float


class MilvusAccessService:
    """Thin wrapper around Milvus Lite collection search operations."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._collection_name = settings.milvus_collection
        self._client = MilvusClient(uri=settings.milvus_lite_uri)

    def ensure_collection(self) -> None:
        """Create collection if missing with cosine metric and required fields."""

        if self._client.has_collection(collection_name=self._collection_name):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            dimension=self._settings.embedding_dimensions,
            metric_type="COSINE",
            consistency_level="Strong",
        )

    def upsert_rows(self, rows: list[tuple[str, str, tuple[float, ...]]]) -> None:
        """Replace collection contents with provided embedding rows."""

        if self._client.has_collection(collection_name=self._collection_name):
            self._client.drop_collection(collection_name=self._collection_name)
        self.ensure_collection()
        if not rows:
            return

        payload: list[dict[str, object]] = []
        for canonical_product_key, embedding_model, vector in rows:
            payload.append(
                {
                    "id": _stable_id(canonical_product_key, embedding_model),
                    "vector": list(vector),
                    "canonical_product_key": canonical_product_key,
                    "embedding_model": embedding_model,
                }
            )
        self._client.insert(collection_name=self._collection_name, data=payload)

    def row_count(self) -> int:
        """Return current number of rows in the Milvus collection."""

        if not self._client.has_collection(collection_name=self._collection_name):
            return 0
        stats = self._client.get_collection_stats(collection_name=self._collection_name)
        row_count_value = stats.get("row_count")
        if isinstance(row_count_value, int):
            return row_count_value
        if isinstance(row_count_value, str):
            return int(row_count_value)
        return 0

    def search(
        self,
        *,
        query_vector: tuple[float, ...],
        embedding_model: str,
        candidate_limit: int,
    ) -> list[VectorMatch]:
        """Search Milvus and return ranked canonical keys with cosine scores."""

        if not query_vector:
            return []

        result_batches = self._client.search(
            collection_name=self._collection_name,
            data=[list(query_vector)],
            limit=candidate_limit,
            filter=f'embedding_model == "{embedding_model}"',
            output_fields=["canonical_product_key"],
        )
        if not result_batches:
            return []

        matches: list[VectorMatch] = []
        for row in result_batches[0]:
            entity_obj = row.get("entity")
            if not isinstance(entity_obj, dict):
                continue
            product_key_obj = entity_obj.get("canonical_product_key")
            if not isinstance(product_key_obj, str):
                continue
            distance_value = row.get("distance")
            matches.append(
                VectorMatch(
                    canonical_product_key=product_key_obj,
                    semantic_score=_to_semantic_score(distance_value),
                )
            )
        return matches


def _stable_id(canonical_product_key: str, embedding_model: str) -> int:
    digest = hashlib.sha256(f"{canonical_product_key}::{embedding_model}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) >> 1


def _to_semantic_score(distance_value: object) -> float:
    if isinstance(distance_value, int | float):
        return float(distance_value)
    if isinstance(distance_value, str):
        return float(distance_value)
    return 0.0
