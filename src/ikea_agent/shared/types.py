"""Typed contracts for retrieval and chat runtime workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MarketCode = Literal["DE"]
EmbeddingProvider = Literal["pydantic_ai_google"]
SortMode = Literal["relevance", "price_asc", "price_desc", "size"]


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
    """EUR price range filter for Germany market scope."""

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
    """Hydrated retrieval output for UI and agent tool use."""

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

    def to_short_result(self) -> ShortRetrievalResult:
        """Project retrieval payload into tool-safe short result shape."""

        return ShortRetrievalResult(
            product_id=self.canonical_product_key,
            product_name=self.product_name,
            product_type=self.product_type,
            description_text=self.description_text,
            main_category=self.main_category,
            sub_category=self.sub_category,
            width_cm=self.width_cm,
            depth_cm=self.depth_cm,
            height_cm=self.height_cm,
            price_eur=self.price_eur,
        )


@dataclass(frozen=True, slots=True)
class ShortRetrievalResult:
    """Lightweight retrieval result for agent tools."""

    product_id: str
    product_name: str
    product_type: str | None
    description_text: str | None
    main_category: str | None
    sub_category: str | None
    width_cm: float | None
    depth_cm: float | None
    height_cm: float | None
    price_eur: float | None

    @staticmethod
    def from_retrieval_result(result: RetrievalResult) -> ShortRetrievalResult:
        """Build short result from a full retrieval result record."""

        return ShortRetrievalResult(
            product_id=result.canonical_product_key,
            product_name=result.product_name,
            product_type=result.product_type,
            description_text=result.description_text,
            main_category=result.main_category,
            sub_category=result.sub_category,
            width_cm=result.width_cm,
            depth_cm=result.depth_cm,
            height_cm=result.height_cm,
            price_eur=result.price_eur,
        )


@dataclass(frozen=True, slots=True)
class SearchResultDiversityWarning:
    """Machine-readable warning for concentrated or repetitive search outputs."""

    kind: Literal["high_family_concentration"]
    message: str
    dominant_family: str
    dominant_share: float
    analyzed_result_count: int


@dataclass(frozen=True, slots=True)
class SearchGraphToolResult:
    """Structured output returned by `run_search_graph` for agent consumption."""

    results: list[ShortRetrievalResult]
    total_candidates: int
    returned_count: int
    warning: SearchResultDiversityWarning | None = None


@dataclass(frozen=True, slots=True)
class SearchQueryInput:
    """One query object consumed by the batched search tool."""

    query_id: str
    semantic_query: str
    limit: int = 20
    candidate_pool_limit: int | None = None
    filters: RetrievalFilters = RetrievalFilters()
    enable_diversification: bool = True
    purpose: str | None = None


@dataclass(frozen=True, slots=True)
class SearchQueryToolResult:
    """Structured output for one query inside a batched search tool call."""

    query_id: str
    semantic_query: str
    results: list[ShortRetrievalResult]
    total_candidates: int
    returned_count: int
    warning: SearchResultDiversityWarning | None = None


@dataclass(frozen=True, slots=True)
class SearchBatchToolResult:
    """Structured output returned by batched `run_search_graph` calls."""

    queries: list[SearchQueryToolResult]


@dataclass(frozen=True, slots=True)
class BundleProposalItemInput:
    """One requested bundle line before catalog hydration."""

    item_id: str
    quantity: int
    reason: str


@dataclass(frozen=True, slots=True)
class BundleValidationResult:
    """Validation outcome for a proposed bundle."""

    kind: Literal["budget_max_eur"]
    status: Literal["pass", "fail", "unknown"]
    message: str


@dataclass(frozen=True, slots=True)
class BundleProposalLineItem:
    """Hydrated line item returned for one bundle proposal."""

    item_id: str
    product_name: str
    description_text: str | None
    price_eur: float | None
    quantity: int
    line_total_eur: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class BundleProposalToolResult:
    """Structured bundle payload rendered outside the chat transcript."""

    bundle_id: str
    title: str
    notes: str | None
    budget_cap_eur: float | None
    items: list[BundleProposalLineItem]
    bundle_total_eur: float | None
    validations: list[BundleValidationResult]
    created_at: str
    run_id: str | None


@dataclass(frozen=True, slots=True)
class AttachmentRef:
    """Attachment pointer passed between upload UX, agent inputs, and tool outputs."""

    attachment_id: str
    mime_type: str
    uri: str
    width: int | None
    height: int | None
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class ImageToolOutput:
    """Typed image payload returned by image-producing tools."""

    caption: str
    images: list[AttachmentRef]
