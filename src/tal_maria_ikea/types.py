"""Typed interfaces for the planned retrieval and ranking pipeline.

This module defines pure data contracts and protocol boundaries so we can scaffold
components independently. Implementations are intentionally deferred.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

PipelineStage = Literal["load", "embed", "persist", "rerank"]


@dataclass(frozen=True, slots=True)
class IkeaRecord:
    """Normalized single catalog row consumed by embedding and ranking steps."""

    product_id: str
    product_name: str
    category: str
    description: str
    dimensions_text: str
    price_text: str


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """Batch payload sent to an embedding backend."""

    records: Sequence[IkeaRecord]
    model_name: str


@dataclass(frozen=True, slots=True)
class EmbeddedRecord:
    """Catalog row plus generated vector representation."""

    record: IkeaRecord
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class QueryContext:
    """Runtime context for user search requests and auditability."""

    query_id: str
    query_text: str
    limit: int


@dataclass(frozen=True, slots=True)
class RankedResult:
    """Result object returned by reranking, before UI adaptation."""

    product_id: str
    score: float
    reason: str


class CatalogLoader(Protocol):
    """Loads and normalizes catalog records from local storage."""

    def load(self) -> Sequence[IkeaRecord]:
        """Return normalized catalog records."""


class EmbeddingGenerator(Protocol):
    """Generates vectors for a normalized catalog batch."""

    def embed(self, request: EmbeddingRequest) -> Sequence[EmbeddedRecord]:
        """Return records with vectors attached."""


class VectorStore(Protocol):
    """Persists and queries embedded records in local storage."""

    def upsert(self, records: Sequence[EmbeddedRecord]) -> None:
        """Write or replace embedded rows in storage."""

    def search(self, query: QueryContext) -> Sequence[EmbeddedRecord]:
        """Return candidate results before reranking."""


class Reranker(Protocol):
    """Rescores candidate records against a user query."""

    def rerank(
        self,
        query: QueryContext,
        candidates: Sequence[EmbeddedRecord],
    ) -> Sequence[RankedResult]:
        """Return ranked candidates with explanations."""
