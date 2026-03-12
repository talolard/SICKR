"""Typed request/response contracts for image analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ikea_agent.shared.types import AttachmentRef, RoomType

RoomEvidenceConfidence = Literal["high", "medium", "low"]
CrossImageRoomRelationship = Literal[
    "same_room_likely",
    "different_rooms_confirmed",
    "uncertain",
]


def _normalize_string_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw_value in values:
        value = raw_value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


class AttachmentRefPayload(BaseModel):
    """JSON-serializable attachment reference used by tool inputs and outputs."""

    attachment_id: str
    mime_type: str
    uri: str
    width: int | None = None
    height: int | None = None
    file_name: str | None = None

    @classmethod
    def from_ref(cls, ref: AttachmentRef) -> AttachmentRefPayload:
        """Build payload model from the runtime dataclass variant."""

        return cls(
            attachment_id=ref.attachment_id,
            mime_type=ref.mime_type,
            uri=ref.uri,
            width=ref.width,
            height=ref.height,
            file_name=ref.file_name,
        )


class ImageToolEnvelope(BaseModel):
    """Common response shape expected by CopilotKit image renderers."""

    caption: str
    images: list[AttachmentRefPayload] = Field(default_factory=list)


class ObjectDetectionRequest(BaseModel):
    """Request payload for object detection on one uploaded image."""

    image: AttachmentRefPayload
    include_overlay_image: bool = True


class DepthEstimationRequest(BaseModel):
    """Request payload for marigold depth estimation."""

    image: AttachmentRefPayload
    ensemble_size: int = Field(default=10, ge=1, le=50)
    processing_res: int = Field(default=768, ge=128, le=4096)
    resample_method: Literal["bilinear", "nearest", "bicubic"] = "bilinear"
    seed: int = 42
    output_format: Literal["png", "jpg", "webp"] = "png"


class SegmentationRequest(BaseModel):
    """Request payload for SAM-3 segmentation on one uploaded image."""

    image: AttachmentRefPayload
    prompt: str | None = Field(default=None, min_length=1, max_length=500)
    queries: list[str] = Field(default_factory=list, max_length=32)
    return_multiple_masks: bool = True
    max_masks: int = Field(default=32, ge=1, le=32)
    include_scores: bool = True
    include_boxes: bool = True
    include_mask_file: bool = True
    apply_mask: bool = False
    output_format: Literal["jpeg", "png", "webp"] = "png"
    sync_mode: bool = False

    @model_validator(mode="after")
    def _require_prompt_or_queries(self) -> SegmentationRequest:
        normalized_queries = [query.strip() for query in self.queries if query.strip()]
        prompt = self.prompt.strip() if self.prompt is not None else ""
        if not normalized_queries and not prompt:
            msg = "SegmentationRequest requires `prompt` or at least one non-empty query."
            raise ValueError(msg)
        self.queries = normalized_queries
        self.prompt = prompt or None
        return self


class ObjectDetectionOptions(BaseModel):
    """Optional knobs for the combined room-photo analysis tool."""

    include_overlay_image: bool = True


class DepthEstimationOptions(BaseModel):
    """Optional depth knobs for the combined room-photo analysis tool."""

    ensemble_size: int = Field(default=10, ge=1, le=50)
    processing_res: int = Field(default=768, ge=128, le=4096)
    resample_method: Literal["bilinear", "nearest", "bicubic"] = "bilinear"
    seed: int = 42
    output_format: Literal["png", "jpg", "webp"] = "png"


class RoomPhotoAnalysisRequest(BaseModel):
    """One-call request that combines room object detection and depth analysis."""

    image: AttachmentRefPayload
    run_object_detection: bool = True
    run_depth: bool = True
    object_detection: ObjectDetectionOptions = Field(default_factory=ObjectDetectionOptions)
    depth_estimation: DepthEstimationOptions = Field(default_factory=DepthEstimationOptions)


class DetectedObject(BaseModel):
    """One detected object with normalized and pixel-space bounding boxes."""

    label: str
    bbox_xyxy_px: tuple[int, int, int, int]
    bbox_xyxy_norm: tuple[float, float, float, float]


class ObjectDetectionToolResult(ImageToolEnvelope):
    """Result payload for Florence object detection."""

    model_id: Literal["fal-ai/florence-2-large/object-detection"]
    image_width_px: int
    image_height_px: int
    detections: list[DetectedObject] = Field(default_factory=list)


class DepthParametersUsed(BaseModel):
    """Echoed marigold generation controls used by the call."""

    ensemble_size: int
    processing_res: int
    resample_method: Literal["bilinear", "nearest", "bicubic"]
    seed: int
    output_format: Literal["png", "jpg", "webp"]


class DepthEstimationToolResult(ImageToolEnvelope):
    """Result payload for Marigold depth estimation."""

    model_id: Literal["fal-ai/imageutils/marigold-depth"]
    depth_image: AttachmentRefPayload | None
    visualization_image: AttachmentRefPayload | None
    parameters_used: DepthParametersUsed


class SegmentationMask(BaseModel):
    """One segmentation mask artifact with optional SAM confidence/box metadata."""

    label: str
    query: str | None = None
    score: float | None = None
    bbox_xyxy_px: tuple[int, int, int, int] | None = None
    mask_image: AttachmentRefPayload


class SegmentationQueryResult(BaseModel):
    """Per-query summary for aggregate segmentation prompts."""

    query: str
    status: Literal["matched", "unattributed", "no_match"]
    matched_mask_count: int


class SegmentationToolResult(ImageToolEnvelope):
    """Result payload for SAM segmentation with optional overlay artifact."""

    model_id: Literal["fal-ai/sam-3/image"]
    prompt: str
    queries: list[str] = Field(default_factory=list)
    query_results: list[SegmentationQueryResult] = Field(default_factory=list)
    analysis_id: str | None = None
    masks: list[SegmentationMask] = Field(default_factory=list)
    overlay_image: AttachmentRefPayload | None = None


class RoomPhotoAnalysisToolResult(ImageToolEnvelope):
    """Combined room-photo understanding payload used by the agent."""

    object_detection: ObjectDetectionToolResult | None = None
    depth: DepthEstimationToolResult | None = None
    room_hints: list[str] = Field(default_factory=list)


class RoomDetailDetailsFromPhotoRequest(BaseModel):
    """Request payload for one structured Gemini room-detail extraction call."""

    model_config = ConfigDict(extra="forbid")

    images: list[AttachmentRefPayload] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _require_image_mime_types(self) -> RoomDetailDetailsFromPhotoRequest:
        non_images = [
            image.attachment_id for image in self.images if not image.mime_type.startswith("image/")
        ]
        if non_images:
            joined = ", ".join(non_images)
            msg = f"RoomDetailDetailsFromPhotoRequest requires image attachments: {joined}"
            raise ValueError(msg)
        return self


class RoomDetailObjectsOfInterest(BaseModel):
    """Grouped object labels returned by room-detail extraction."""

    model_config = ConfigDict(extra="forbid")

    major_furniture: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    lifestyle_indicators: list[str] = Field(default_factory=list)
    other_items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_labels(self) -> RoomDetailObjectsOfInterest:
        self.major_furniture = _normalize_string_list(self.major_furniture)
        self.fixtures = _normalize_string_list(self.fixtures)
        self.lifestyle_indicators = _normalize_string_list(self.lifestyle_indicators)
        self.other_items = _normalize_string_list(self.other_items)
        return self


class RoomPhotoImageAssessment(BaseModel):
    """Per-image room assessment used to preserve ambiguity across multiple photos."""

    model_config = ConfigDict(extra="forbid")

    image_index: int = Field(ge=0)
    appears_to_show_room: bool | None = None
    room_type: RoomType = "unknown"
    confidence: RoomEvidenceConfidence = "low"
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_notes(self) -> RoomPhotoImageAssessment:
        self.notes = _normalize_string_list(self.notes)
        return self


class RoomDetailDetailsFromPhotoResult(BaseModel):
    """Structured result returned by `get_room_detail_details_from_photo`."""

    model_config = ConfigDict(extra="forbid")

    caption: str = "Room detail analysis complete."
    room_type: RoomType = "unknown"
    confidence: RoomEvidenceConfidence = "low"
    all_images_appear_to_show_rooms: bool | None = None
    non_room_image_indices: list[int] = Field(default_factory=list)
    cross_image_room_relationship: CrossImageRoomRelationship = "uncertain"
    objects_of_interest: RoomDetailObjectsOfInterest = Field(
        default_factory=RoomDetailObjectsOfInterest
    )
    image_assessments: list[RoomPhotoImageAssessment] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_result(self) -> RoomDetailDetailsFromPhotoResult:
        seen_indices: set[int] = set()
        normalized_indices: list[int] = []
        for index in self.non_room_image_indices:
            if index < 0 or index in seen_indices:
                continue
            seen_indices.add(index)
            normalized_indices.append(index)
        self.non_room_image_indices = normalized_indices
        self.notes = _normalize_string_list(self.notes)
        return self
