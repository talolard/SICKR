"""fal.ai image analysis tools and typed contracts."""

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    SegmentationRequest,
    SegmentationToolResult,
)
from ikea_agent.tools.image_analysis.tool import (
    analyze_room_photo,
    detect_objects_in_image,
    estimate_depth_map,
    segment_image_with_prompt,
)

__all__ = [
    "AttachmentRefPayload",
    "DepthEstimationRequest",
    "DepthEstimationToolResult",
    "ObjectDetectionRequest",
    "ObjectDetectionToolResult",
    "RoomPhotoAnalysisRequest",
    "RoomPhotoAnalysisToolResult",
    "SegmentationRequest",
    "SegmentationToolResult",
    "analyze_room_photo",
    "detect_objects_in_image",
    "estimate_depth_map",
    "segment_image_with_prompt",
]
