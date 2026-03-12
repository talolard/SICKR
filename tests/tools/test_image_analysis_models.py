from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
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


def test_room_detail_result_normalizes_grouped_labels_and_notes() -> None:
    result = RoomDetailDetailsFromPhotoResult.model_validate(
        {
            "caption": "Room detail analysis complete.",
            "room_type": "living_room",
            "objects_of_interest": {
                "major_furniture": [" sofa ", "sofa", "coffee table"],
                "fixtures": ["radiator", " radiator "],
                "lifestyle_indicators": ["cat", "cat"],
                "other_items": ["rug", " rug "],
            },
            "image_assessments": [
                {
                    "image_index": 0,
                    "appears_to_show_room": True,
                    "room_type": "living_room",
                    "confidence": "high",
                    "notes": [" bright room ", "bright room"],
                }
            ],
            "notes": [" open shelving ", "open shelving"],
            "non_room_image_indices": [2, 2, 1],
        }
    )

    assert result.objects_of_interest == RoomDetailObjectsOfInterest(
        major_furniture=["sofa", "coffee table"],
        fixtures=["radiator"],
        lifestyle_indicators=["cat"],
        other_items=["rug"],
    )
    assert result.image_assessments == [
        RoomPhotoImageAssessment(
            image_index=0,
            appears_to_show_room=True,
            room_type="living_room",
            confidence="high",
            notes=["bright room"],
        )
    ]
    assert result.notes == ["open shelving"]
    assert result.non_room_image_indices == [2, 1]
