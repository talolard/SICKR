"""Typed request/response contracts for fal.ai-backed image analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ikea_agent.shared.types import AttachmentRef


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
    """Request payload for prompt-driven SAM segmentation."""

    image: AttachmentRefPayload
    prompt: str = Field(min_length=1, max_length=300)
    return_multiple_masks: bool = False
    mask_limit: int = Field(default=5, ge=1, le=10)
    keep_model_loaded: bool = False


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
    """One prompt-associated segmentation mask artifact."""

    label: str
    mask_image: AttachmentRefPayload


class SegmentationToolResult(ImageToolEnvelope):
    """Result payload for SAM segmentation with optional overlay artifact."""

    model_id: Literal["fal-ai/sam-3/image"]
    prompt: str
    masks: list[SegmentationMask] = Field(default_factory=list)
    overlay_image: AttachmentRefPayload | None = None


class RoomPhotoAnalysisToolResult(ImageToolEnvelope):
    """Combined room-photo understanding payload used by the agent."""

    object_detection: ObjectDetectionToolResult | None = None
    depth: DepthEstimationToolResult | None = None
    room_hints: list[str] = Field(default_factory=list)
