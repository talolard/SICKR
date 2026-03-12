from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    RoomDetailDetailsExtraction,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailObjectsOfInterest,
    RoomPhotoAnalysisRequest,
    RoomPhotoImageAssessment,
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


def test_segmentation_request_rejects_invalid_max_masks() -> None:
    with pytest.raises(ValidationError):
        SegmentationRequest.model_validate(
            {
                "image": _attachment().model_dump(),
                "prompt": "clutter",
                "max_masks": 0,
            }
        )


def test_segmentation_request_requires_prompt_or_queries() -> None:
    with pytest.raises(ValidationError):
        SegmentationRequest.model_validate(
            {
                "image": _attachment().model_dump(),
                "queries": ["", "   "],
            }
        )


def test_segmentation_request_normalizes_queries() -> None:
    request = SegmentationRequest.model_validate(
        {
            "image": _attachment().model_dump(),
            "queries": [" bed ", "clutter", ""],
            "max_masks": 32,
        }
    )

    assert request.queries == ["bed", "clutter"]
    assert request.max_masks == 32
    assert request.return_multiple_masks is True


def test_combined_room_analysis_defaults() -> None:
    request = RoomPhotoAnalysisRequest(image=_attachment())

    assert request.run_object_detection is True
    assert request.run_depth is True
    assert request.object_detection.include_overlay_image is True


def test_room_detail_request_rejects_duplicate_attachment_ids() -> None:
    with pytest.raises(ValidationError):
        RoomDetailDetailsFromPhotoRequest.model_validate(
            {
                "images": [
                    _attachment().model_dump(),
                    _attachment().model_dump(),
                ]
            }
        )


def test_room_detail_request_rejects_non_image_attachment() -> None:
    with pytest.raises(ValidationError):
        RoomDetailDetailsFromPhotoRequest.model_validate(
            {
                "images": [
                    {
                        **_attachment().model_dump(),
                        "mime_type": "application/pdf",
                    }
                ]
            }
        )


def test_room_detail_extraction_defaults_are_stable() -> None:
    extraction = RoomDetailDetailsExtraction()

    assert extraction.room_type == "unknown"
    assert extraction.cross_image_room_relationship == "uncertain"
    assert extraction.objects_of_interest == RoomDetailObjectsOfInterest()
    assert extraction.image_assessments == []


def test_room_photo_image_assessment_accepts_zero_based_indices() -> None:
    assessment = RoomPhotoImageAssessment(
        image_index=0,
        appears_to_show_room=True,
        room_type="living_room",
        confidence="high",
        notes=["Large sofa visible."],
    )

    assert assessment.image_index == 0
    assert assessment.notes == ["Large sofa visible."]
