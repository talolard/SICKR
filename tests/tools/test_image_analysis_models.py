from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    RoomPhotoAnalysisRequest,
    SegmentationRequest,
)


def _attachment() -> AttachmentRefPayload:
    return AttachmentRefPayload(
        attachment_id="att-1",
        mime_type="image/png",
        uri="/attachments/att-1",
        width=640,
        height=480,
        file_name="room.png",
    )


def test_depth_request_defaults_are_stable() -> None:
    request = DepthEstimationRequest(image=_attachment())

    assert request.ensemble_size == 10
    assert request.processing_res == 768
    assert request.output_format == "png"


def test_segmentation_request_rejects_invalid_mask_limit() -> None:
    with pytest.raises(ValidationError):
        SegmentationRequest.model_validate(
            {
                "image": _attachment().model_dump(),
                "prompt": "clutter",
                "mask_limit": 0,
            }
        )


def test_combined_room_analysis_defaults() -> None:
    request = RoomPhotoAnalysisRequest(image=_attachment())

    assert request.run_object_detection is True
    assert request.run_depth is True
    assert request.object_detection.include_overlay_image is True
