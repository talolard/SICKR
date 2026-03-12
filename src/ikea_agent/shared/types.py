"""Typed contracts for retrieval and chat runtime workflows.

The retrieval layer mostly uses lightweight frozen dataclasses, while tool-facing
bundle payloads use Pydantic models so they can flow through agent state,
runtime persistence, and FastAPI responses without losing validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SortMode = Literal["relevance", "price_asc", "price_desc", "size"]
RoomType = Literal[
    "bathroom",
    "bedroom",
    "dining_room",
    "entryway",
    "hallway",
    "home_office",
    "kitchen",
    "laundry_room",
    "living_room",
    "nursery",
    "outdoor",
    "studio",
    "utility_room",
    "other",
    "unknown",
]


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


BundleValidationKind = Literal[
    "budget_max_eur",
    "pricing_complete",
    "duplicate_items",
]
BundleValidationStatus = Literal["pass", "warn", "fail", "unknown"]


class BundleProposalItemInput(BaseModel):
    """One requested bundle line before catalog hydration.

    This is a tool input model, so we keep validation close to the boundary and
    reject impossible quantities before catalog hydration begins.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str
    quantity: int = Field(ge=1)
    reason: str


class BundleValidationResult(BaseModel):
    """Validation outcome for a proposed bundle."""

    model_config = ConfigDict(extra="forbid")

    kind: BundleValidationKind
    status: BundleValidationStatus
    message: str


class BundleProposalLineItem(BaseModel):
    """Hydrated line item returned for one bundle proposal."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    product_name: str
    description_text: str | None
    price_eur: float | None
    quantity: int = Field(ge=1)
    line_total_eur: float | None
    reason: str


class BundleProposalToolResult(BaseModel):
    """Structured bundle payload rendered outside the chat transcript."""

    model_config = ConfigDict(extra="forbid")

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
