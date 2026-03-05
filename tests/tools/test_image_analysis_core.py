from __future__ import annotations

import asyncio
import os
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.image_analysis.core import FalImageAnalysisCore
from ikea_agent.tools.image_analysis.models import AttachmentRefPayload


def _png_bytes(width: int = 32, height: int = 24) -> bytes:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _attachment_payload(store: AttachmentStore) -> AttachmentRefPayload:
    stored = store.save_image_bytes(
        content=_png_bytes(), mime_type="image/png", filename="room.png"
    )
    return AttachmentRefPayload.from_ref(stored.ref)


def test_prepare_image_supports_fai_ai_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _attachment_payload(store)
    core = FalImageAnalysisCore(store)

    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setenv("FAI_AI_API_KEY", "test-fal-key")

    async def _fake_upload(path: Path) -> str:
        _ = path
        return "https://fal.example/uploaded-image"

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.core.fal_client.upload_file_async", _fake_upload
    )

    prepared = asyncio.run(core.prepare_image(payload))

    assert prepared.fal_image_url == "https://fal.example/uploaded-image"
    assert prepared.width == 32
    assert prepared.height == 24
    assert os.environ["FAL_KEY"] == "test-fal-key"


def test_parse_object_detections_normalizes_boxes() -> None:
    payload = {
        "detections": [
            {"label": "chair", "bbox": [10, 20, 110, 120]},
            {"label": "table", "bbox": {"x1": 20, "y1": 30, "x2": 200, "y2": 250}},
        ]
    }

    detections = FalImageAnalysisCore.parse_object_detections(
        payload,
        image_width=400,
        image_height=300,
    )

    assert [item.label for item in detections] == ["chair", "table"]
    assert detections[0].bbox_xyxy_px == (10, 20, 110, 120)
    assert detections[0].bbox_xyxy_norm == (0.025, 0.066667, 0.275, 0.4)
