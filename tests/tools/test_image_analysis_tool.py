from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from PIL import Image
from pydantic_ai import BinaryContent

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.image_analysis import get_room_detail_details_from_photo
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    ObjectDetectionRequest,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomPhotoAnalysisRequest,
    SegmentationRequest,
)
from ikea_agent.tools.image_analysis.room_detail_tool import RoomDetailDetailsService
from ikea_agent.tools.image_analysis.tool import (
    analyze_room_photo,
    detect_objects_in_image,
    estimate_depth_map,
    segment_image_with_prompt,
)


def _make_image_bytes() -> bytes:
    image = Image.new("RGB", (320, 240), color=(240, 240, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _store_attachment(store: AttachmentStore) -> AttachmentRefPayload:
    stored = store.save_image_bytes(
        content=_make_image_bytes(), mime_type="image/png", filename="room.png"
    )
    return AttachmentRefPayload.from_ref(stored.ref)


def test_detect_objects_in_image_wrapper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _store_attachment(store)

    async def _fake_call_model(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        return {"detections": [{"label": "chair", "bbox": [10, 20, 100, 130]}]}

    monkeypatch.setenv("FAI_AI_API_KEY", "test-fal-key")
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.fal_client.upload_file_async", _fake_upload
    )
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.call_model",
        _fake_call_model,
    )

    result = asyncio.run(
        detect_objects_in_image(
            request=ObjectDetectionRequest(image=payload, include_overlay_image=True),
            attachment_store=store,
        )
    )

    assert result.detections
    assert result.detections[0].label == "chair"
    assert result.images


async def _fake_upload(path: Path) -> str:
    _ = path
    return "https://fal.example/uploaded-room"


def test_depth_and_segmentation_wrappers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _store_attachment(store)
    remote_depth = "https://fal.example/depth.png"
    remote_visual = "https://fal.example/visual.png"
    remote_mask = "https://fal.example/mask.png"

    async def _fake_call_depth(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        return {
            "depth": {"url": remote_depth},
            "visualization": {"url": remote_visual},
        }

    segmentation_arguments: dict[str, object] = {}

    async def _fake_call_segmentation(*args: object, **kwargs: object) -> dict[str, object]:
        _ = args
        segmentation_arguments.update(cast("dict[str, object]", kwargs.get("arguments", {})))
        return {
            "masks": [{"label": "clutter", "url": remote_mask}],
            "scores": [0.93],
            "boxes": [[12, 24, 120, 180]],
        }

    async def _fake_download(*args: object, **kwargs: object) -> AttachmentRefPayload:
        _ = args
        stored = store.save_image_bytes(
            content=_make_image_bytes(),
            mime_type="image/png",
            filename=cast("str", kwargs["fallback_filename"]),
        )
        return AttachmentRefPayload.from_ref(stored.ref)

    monkeypatch.setenv("FAI_AI_API_KEY", "test-fal-key")
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.fal_client.upload_file_async", _fake_upload
    )
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.download_to_attachment",
        _fake_download,
    )

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.call_model",
        _fake_call_depth,
    )
    depth_result = asyncio.run(
        estimate_depth_map(
            request=DepthEstimationRequest(image=payload),
            attachment_store=store,
        )
    )
    assert depth_result.images

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.call_model",
        _fake_call_segmentation,
    )
    segmentation_result = asyncio.run(
        segment_image_with_prompt(
            request=SegmentationRequest(
                image=payload,
                queries=["clutter", "laundry"],
                return_multiple_masks=True,
                max_masks=32,
            ),
            attachment_store=store,
        )
    )
    assert segmentation_result.masks
    assert segmentation_result.overlay_image is not None
    assert segmentation_result.prompt == "clutter, laundry"
    assert segmentation_result.queries == ["clutter", "laundry"]
    assert segmentation_result.query_results[0].status == "unattributed"
    assert segmentation_result.masks[0].score == pytest.approx(0.93)
    assert segmentation_result.masks[0].bbox_xyxy_px == (12, 24, 120, 180)
    assert segmentation_result.masks[0].query is None
    assert segmentation_arguments["max_masks"] == 32


def test_analyze_room_photo_wrapper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _store_attachment(store)

    async def _fake_call_model(
        self: object,
        *,
        model_id: str,
        arguments: dict[str, object],
        start_timeout: float,
        client_timeout: float,
    ) -> dict[str, object]:
        _ = (self, arguments, start_timeout, client_timeout)
        if model_id.endswith("object-detection"):
            return {"detections": [{"label": "sofa", "bbox": [0, 0, 100, 100]}]}
        return {"depth": {"url": "https://fal.example/depth.png"}}

    async def _fake_download(*args: object, **kwargs: object) -> AttachmentRefPayload:
        _ = args
        stored = store.save_image_bytes(
            content=_make_image_bytes(),
            mime_type="image/png",
            filename=cast("str", kwargs["fallback_filename"]),
        )
        return AttachmentRefPayload.from_ref(stored.ref)

    monkeypatch.setenv("FAI_AI_API_KEY", "test-fal-key")
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.fal_client.upload_file_async", _fake_upload
    )
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.call_model",
        _fake_call_model,
    )
    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.FalImageAnalysisCore.download_to_attachment",
        _fake_download,
    )

    result = asyncio.run(
        analyze_room_photo(
            request=RoomPhotoAnalysisRequest(image=payload),
            attachment_store=store,
        )
    )

    assert result.object_detection is not None
    assert result.depth is not None
    assert result.room_hints


def test_get_room_detail_details_from_photo_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload_a = _store_attachment(store)
    payload_b = _store_attachment(store)
    captured_content: dict[str, object] = {}

    async def _fake_run_extractor(
        self: RoomDetailDetailsService,
        user_content: list[str | BinaryContent],
    ) -> RoomDetailDetailsFromPhotoResult:
        _ = self
        captured_content["user_content"] = user_content
        return RoomDetailDetailsFromPhotoResult(
            caption="Room detail analysis complete.",
            room_type="living_room",
            confidence="high",
            all_images_appear_to_show_rooms=True,
            cross_image_room_relationship="same_room_likely",
            objects_of_interest={
                "major_furniture": ["sofa"],
                "fixtures": ["radiator"],
                "lifestyle_indicators": ["cat"],
                "other_items": ["rug"],
            },
            image_assessments=[
                {
                    "image_index": 0,
                    "appears_to_show_room": True,
                    "room_type": "living_room",
                    "confidence": "high",
                    "notes": ["Wide shot"],
                },
                {
                    "image_index": 1,
                    "appears_to_show_room": True,
                    "room_type": "living_room",
                    "confidence": "medium",
                    "notes": ["Side angle"],
                },
            ],
            notes=["Pet-visible living room."],
        )

    monkeypatch.setattr(RoomDetailDetailsService, "_run_extractor", _fake_run_extractor)

    result = asyncio.run(
        get_room_detail_details_from_photo(
            request=RoomDetailDetailsFromPhotoRequest(images=[payload_a, payload_b]),
            attachment_store=store,
        )
    )

    assert result.room_type == "living_room"
    user_content = cast("list[str | BinaryContent]", captured_content["user_content"])
    assert len(user_content) == 3
    assert user_content[0] == "Analyze the attached room photos for interior-design context."
    assert isinstance(user_content[1], BinaryContent)
    assert isinstance(user_content[2], BinaryContent)


def test_get_room_detail_details_from_photo_wrapper_rejects_missing_attachment(
    tmp_path: Path,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")

    with pytest.raises(ValueError, match="Attachment not found: missing-image"):
        asyncio.run(
            get_room_detail_details_from_photo(
                request=RoomDetailDetailsFromPhotoRequest(
                    images=[
                        AttachmentRefPayload(
                            attachment_id="missing-image",
                            mime_type="image/png",
                            uri="/attachments/missing-image",
                            width=640,
                            height=480,
                            file_name="missing.png",
                        )
                    ]
                ),
                attachment_store=store,
            )
        )
