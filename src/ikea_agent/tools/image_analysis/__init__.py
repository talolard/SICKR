"""fal.ai image analysis tools and typed contracts."""

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    CrossImageRoomRelationship,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomDetailObjectsOfInterest,
    RoomEvidenceConfidence,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    RoomPhotoImageAssessment,
    SegmentationRequest,
    SegmentationToolResult,
)
from ikea_agent.tools.image_analysis.room_detail_tool import (
    RoomDetailDetailsError,
    build_room_detail_details_extractor,
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
    "CrossImageRoomRelationship",
    "DepthEstimationRequest",
    "DepthEstimationToolResult",
    "ObjectDetectionRequest",
    "ObjectDetectionToolResult",
    "RoomDetailDetailsError",
    "RoomDetailDetailsFromPhotoRequest",
    "RoomDetailDetailsFromPhotoResult",
    "RoomDetailObjectsOfInterest",
    "RoomEvidenceConfidence",
    "RoomPhotoAnalysisRequest",
    "RoomPhotoAnalysisToolResult",
    "RoomPhotoImageAssessment",
    "SegmentationRequest",
    "SegmentationToolResult",
    "analyze_room_photo",
    "build_room_detail_details_extractor",
    "detect_objects_in_image",
    "estimate_depth_map",
    "get_room_detail_details_from_photo",
    "segment_image_with_prompt",
]
