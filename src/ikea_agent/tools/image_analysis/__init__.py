"""Image-analysis tools and typed contracts."""

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomDetailObjectsOfInterest,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    SegmentationRequest,
    SegmentationToolResult,
)
from ikea_agent.tools.image_analysis.room_detail_details import (
    get_room_detail_details_from_photo,
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
    "RoomDetailDetailsFromPhotoRequest",
    "RoomDetailDetailsFromPhotoResult",
    "RoomDetailObjectsOfInterest",
    "RoomPhotoAnalysisRequest",
    "RoomPhotoAnalysisToolResult",
    "SegmentationRequest",
    "SegmentationToolResult",
    "analyze_room_photo",
    "detect_objects_in_image",
    "estimate_depth_map",
    "get_room_detail_details_from_photo",
    "segment_image_with_prompt",
]
