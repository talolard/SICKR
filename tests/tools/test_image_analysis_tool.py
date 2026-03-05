from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from PIL import Image

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    ObjectDetectionRequest,
    RoomPhotoAnalysisRequest,
    SegmentationRequest,
)
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

    async def _fake_call_segmentation(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        return {"masks": [{"label": "clutter", "url": remote_mask}]}

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
                image=payload, prompt="clutter", return_multiple_masks=True
            ),
            attachment_store=store,
        )
    )
    assert segmentation_result.masks
    assert segmentation_result.overlay_image is not None


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
