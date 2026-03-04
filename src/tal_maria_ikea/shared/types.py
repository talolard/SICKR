"""Typed contracts for ingestion, retrieval, web, and evaluation workflows.

The intent of these dataclasses is to keep pipeline boundaries explicit and stable
as we iterate on strategy quality and UI behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MarketCode = Literal["DE"]
EmbeddingProvider = Literal["vertex_gemini"]
SortMode = Literal["relevance", "price_asc", "price_desc", "size"]
QueryExpansionMode = Literal["auto", "on", "off"]
FilterTimingMode = Literal["embed_then_filter", "filter_then_embed"]


@dataclass(frozen=True, slots=True)
class DimensionAxisFilter:
    """Numeric filter controls for one dimension axis in centimeters."""

    exact_cm: float | None = None
    min_cm: float | None = None
    max_cm: float | None = None


@dataclass(frozen=True, slots=True)
class DimensionFilter:
    """Width/depth/height constraints used by retrieval filtering."""

    width: DimensionAxisFilter = DimensionAxisFilter()
    depth: DimensionAxisFilter = DimensionAxisFilter()
    height: DimensionAxisFilter = DimensionAxisFilter()


@dataclass(frozen=True, slots=True)
class PriceFilterEUR:
    """EUR price range filter for Germany market scope.

    The design keeps EUR-specific fields now and can be extended with currency-aware
    policies in a future phase without changing retrieval query signatures.
    """

    min_eur: float | None = None
    max_eur: float | None = None


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Structured filters layered on top of semantic search."""

    category: str | None = None
    include_keyword: str | None = None
    exclude_keyword: str | None = None
    sort: SortMode = "relevance"
    price: PriceFilterEUR = PriceFilterEUR()
    dimensions: DimensionFilter = DimensionFilter()


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Query payload consumed by retrieval service."""

    query_text: str
    result_limit: int
    filters: RetrievalFilters = RetrievalFilters()


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Hydrated retrieval output for UI and evaluation."""

    canonical_product_key: str
    product_name: str
    product_type: str | None
    description_text: str | None
    embedding_text: str | None
    main_category: str | None
    sub_category: str | None
    dimensions_text: str | None
    width_cm: float | None
    depth_cm: float | None
    height_cm: float | None
    price_eur: float | None
    url: str | None
    semantic_score: float
    filter_pass_reasons: tuple[str, ...]
    rank_explanation: str


@dataclass(frozen=True, slots=True)
class EmbeddingInputRow:
    """Catalog row and prebuilt text payload for embedding."""

    canonical_product_key: str
    embedding_text: str


@dataclass(frozen=True, slots=True)
class EmbeddedVectorRow:
    """Embedding output for one product row."""

    canonical_product_key: str
    embedding_text: str
    embedding_vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ShortlistItem:
    """One product entry in global shortlist persistence."""

    canonical_product_key: str
    product_name: str
    product_type: str | None
    main_category: str | None
    sub_category: str | None
    dimensions_text: str | None
    price_eur: float | None
    url: str | None
    note: str | None


@dataclass(frozen=True, slots=True)
class ShortlistState:
    """Current shortlist state returned to template layer."""

    items: tuple[ShortlistItem, ...]


@dataclass(frozen=True, slots=True)
class EvalQuery:
    """Generated evaluation query with coarse intent metadata."""

    eval_query_id: str
    query_text: str
    category_hint: str | None
    intent_kind: str | None


@dataclass(frozen=True, slots=True)
class EvalLabelSet:
    """Expected top-k canonical products for one evaluation query."""

    eval_query_id: str
    expected_top_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalRunMetrics:
    """Aggregate retrieval quality metrics from one evaluation execution."""

    hit_at_k: float
    recall_at_k: float
    mrr: float | None
    total_queries: int
