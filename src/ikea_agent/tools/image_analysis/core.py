"""Shared fal.ai execution core for image-analysis tool wrappers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO
from logging import getLogger
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fal_client
import httpx
from PIL import Image, ImageDraw

from ikea_agent.chat_app.attachments import AttachmentStore, StoredAttachment
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DetectedObject,
)

logger = getLogger(__name__)

FLORENCE_MODEL_ID = "fal-ai/florence-2-large/object-detection"
MARIGOLD_MODEL_ID = "fal-ai/imageutils/marigold-depth"
SAM_MODEL_ID = "fal-ai/sam-3/image"

_OVERLAY_COLORS: tuple[str, ...] = (
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#7c3aed",
    "#ea580c",
    "#0f766e",
)
BBOX_COORDINATE_COUNT = 4


def _scale_mask_alpha(pixel: int) -> int:
    """Reduce mask alpha strength so overlaid masks keep source image visible."""

    return round(pixel * 0.45)


class ImageAnalysisError(ValueError):
    """Raised when one image-analysis call cannot complete successfully."""


@dataclass(frozen=True, slots=True)
class PreparedImage:
    """Resolved local attachment with uploaded fal URL and source dimensions."""

    stored: StoredAttachment
    fal_image_url: str
    width: int
    height: int


class FalImageAnalysisCore:
    """Centralized IO and rendering helpers used by all fal.ai image tools."""

    def __init__(self, attachment_store: AttachmentStore) -> None:
        """Store attachment repository dependency shared by all tool calls."""

        self._attachment_store = attachment_store

    async def prepare_image(self, image: AttachmentRefPayload) -> PreparedImage:
        """Resolve one uploaded image and upload it to fal storage."""

        self._ensure_fal_key_available()
        stored = self._attachment_store.resolve(image.attachment_id)
        if stored is None:
            msg = f"Attachment not found: {image.attachment_id}"
            raise ImageAnalysisError(msg)

        raw_bytes = stored.path.read_bytes()
        try:
            with Image.open(BytesIO(raw_bytes)) as parsed:
                width, height = parsed.size
        except Exception as exc:
            msg = f"Attachment is not a readable image: {image.attachment_id}"
            raise ImageAnalysisError(msg) from exc

        fal_image_url = await fal_client.upload_file_async(stored.path)
        return PreparedImage(stored=stored, fal_image_url=fal_image_url, width=width, height=height)

    async def call_model(
        self,
        *,
        model_id: str,
        arguments: dict[str, Any],
        start_timeout: float,
        client_timeout: float,
    ) -> dict[str, Any]:
        """Run one fal model call and normalize errors into actionable messages."""

        self._ensure_fal_key_available()
        logger.info(
            "fal_model_call_start",
            extra={"model_id": model_id, "argument_keys": sorted(arguments)},
        )
        try:
            # TODO - document why we use subscribe_async instead of a more tradional pattern
            result = await fal_client.subscribe_async(
                model_id,
                arguments=arguments,
                start_timeout=start_timeout,
                client_timeout=client_timeout,
            )
        except Exception as exc:
            msg = f"fal model call failed for {model_id}: {exc}"
            raise ImageAnalysisError(msg) from exc
        if not isinstance(result, dict):
            msg = (
                "fal model returned unexpected payload type for "
                f"{model_id}: {type(result).__name__}"
            )
            raise ImageAnalysisError(msg)
        return result

    async def download_to_attachment(
        self,
        *,
        remote_url: str,
        fallback_filename: str,
        timeout_seconds: float = 45.0,
    ) -> AttachmentRefPayload:
        """Download a remote image URL and store it as a local attachment."""

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(remote_url, follow_redirects=True)
            response.raise_for_status()
        content_type = response.headers.get("content-type", "image/png").split(";")[0].strip()
        stored = self._attachment_store.save_image_bytes(
            content=response.content,
            mime_type=content_type or "image/png",
            filename=self._filename_from_url(remote_url) or fallback_filename,
            created_by_tool="image_analysis",
            kind="analysis_output",
        )
        return AttachmentRefPayload.from_ref(stored.ref)

    def create_detection_overlay(
        self,
        *,
        prepared: PreparedImage,
        detections: list[DetectedObject],
    ) -> AttachmentRefPayload:
        """Draw detection boxes on top of the source image and store the overlay."""
        # TODO - when rendering in the UI, it may be better to send detection
        # coordinates/labels and let the client render overlays, so we avoid
        # generating additional attachment files.
        source_bytes = prepared.stored.path.read_bytes()
        with Image.open(BytesIO(source_bytes)).convert("RGBA") as base:
            draw = ImageDraw.Draw(base)
            for index, detection in enumerate(detections):
                color = _OVERLAY_COLORS[index % len(_OVERLAY_COLORS)]
                x1, y1, x2, y2 = detection.bbox_xyxy_px
                draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
                draw.text((x1 + 4, y1 + 4), detection.label, fill=color)
            output = BytesIO()
            base.save(output, format="PNG")

        stored = self._attachment_store.save_image_bytes(
            content=output.getvalue(),
            mime_type="image/png",
            filename="object-detection-overlay.png",
            created_by_tool="detect_objects_in_image",
            kind="analysis_overlay",
        )
        return AttachmentRefPayload.from_ref(stored.ref)

    def create_segmentation_overlay(
        self,
        *,
        prepared: PreparedImage,
        mask_images: list[AttachmentRefPayload],
    ) -> AttachmentRefPayload:
        """Compose colorized segmentation masks on the source image."""
        # TODO: Likewise - client-side mask rendering might be better. Research
        # tradeoffs and keep this server-side path until a user flow requires it.
        source_bytes = prepared.stored.path.read_bytes()
        with Image.open(BytesIO(source_bytes)).convert("RGBA") as base:
            for index, mask_ref in enumerate(mask_images):
                stored_mask = self._attachment_store.resolve(mask_ref.attachment_id)
                if stored_mask is None:
                    continue
                with Image.open(stored_mask.path).convert("L") as alpha_mask:
                    color = _OVERLAY_COLORS[index % len(_OVERLAY_COLORS)]
                    tint = Image.new("RGBA", base.size, color=color)
                    tint.putalpha(alpha_mask.point(_scale_mask_alpha))
                    base.alpha_composite(tint)
            output = BytesIO()
            base.save(output, format="PNG")

        stored = self._attachment_store.save_image_bytes(
            content=output.getvalue(),
            mime_type="image/png",
            filename="segmentation-overlay.png",
            created_by_tool="segment_image_with_prompt",
            kind="analysis_overlay",
        )
        return AttachmentRefPayload.from_ref(stored.ref)

    @staticmethod
    def parse_image_urls(payload: object) -> list[str]:
        """Extract image URLs from a nested response payload."""

        urls: list[str] = []
        stack: list[Any] = [payload]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if key == "url" and isinstance(value, str) and value.startswith("http"):
                        urls.append(value)
                    else:
                        stack.append(value)
            elif isinstance(current, list):
                stack.extend(current)
        return list(dict.fromkeys(urls))

    @staticmethod
    def parse_object_detections(
        payload: dict[str, Any],
        *,
        image_width: int,
        image_height: int,
    ) -> list[DetectedObject]:
        """Convert flexible response payloads into a stable detection list."""

        candidates = FalImageAnalysisCore._extract_detection_candidates(payload)

        detections: list[DetectedObject] = []
        for item in candidates:
            label = str(item.get("label") or item.get("class_name") or item.get("name") or "object")
            bbox_value = (
                item.get("bbox")
                or item.get("bounding_box")
                or item.get("box")
                or (item if all(key in item for key in ("x", "y", "w", "h")) else None)
            )
            bbox = FalImageAnalysisCore._parse_bbox_px(
                bbox_value,
                image_width=image_width,
                image_height=image_height,
            )
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            norm = (
                round(x1 / max(image_width, 1), 6),
                round(y1 / max(image_height, 1), 6),
                round(x2 / max(image_width, 1), 6),
                round(y2 / max(image_height, 1), 6),
            )
            detections.append(DetectedObject(label=label, bbox_xyxy_px=bbox, bbox_xyxy_norm=norm))
        return detections

    @staticmethod
    def _parse_bbox_px(
        value: object,
        *,
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int] | None:
        extracted = FalImageAnalysisCore._extract_raw_bbox_numbers(value)
        if extracted is None:
            return None
        bbox_floats, is_xywh = extracted

        parsed_floats = FalImageAnalysisCore._coerce_bbox_numbers(bbox_floats)
        if parsed_floats is None:
            return None

        x1_raw, y1_raw, x2_raw, y2_raw = parsed_floats
        if is_xywh:
            x2_raw = x1_raw + x2_raw
            y2_raw = y1_raw + y2_raw

        x1 = max(0, min(round(x1_raw), image_width))
        y1 = max(0, min(round(y1_raw), image_height))
        x2 = max(0, min(round(x2_raw), image_width))
        y2 = max(0, min(round(y2_raw), image_height))
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    @staticmethod
    def _extract_raw_bbox_numbers(value: object) -> tuple[list[object], bool] | None:
        if isinstance(value, list) and len(value) >= BBOX_COORDINATE_COUNT:
            return value[:BBOX_COORDINATE_COUNT], False
        if isinstance(value, dict):
            bbox_floats, is_xywh = FalImageAnalysisCore._bbox_floats_from_dict(value)
            if bbox_floats is not None:
                return bbox_floats, is_xywh
        return None

    @staticmethod
    def _coerce_bbox_numbers(bbox_floats: list[object]) -> list[float] | None:
        parsed_floats: list[float] = []
        for number in bbox_floats:
            if not isinstance(number, (int, float, str)):
                return None
            try:
                parsed_floats.append(float(number))
            except ValueError:
                return None
        if len(parsed_floats) != BBOX_COORDINATE_COUNT:
            return None
        return parsed_floats

    @staticmethod
    def _bbox_floats_from_dict(value: dict[str, object]) -> tuple[list[object] | None, bool]:
        xyxy_key_sets = (
            ("x1", "y1", "x2", "y2"),
            ("left", "top", "right", "bottom"),
        )
        for x1_key, y1_key, x2_key, y2_key in xyxy_key_sets:
            if all(key in value for key in (x1_key, y1_key, x2_key, y2_key)):
                return [value[x1_key], value[y1_key], value[x2_key], value[y2_key]], False
        if all(key in value for key in ("x", "y", "w", "h")):
            return [value["x"], value["y"], value["w"], value["h"]], True
        return None, False

    @staticmethod
    def _filename_from_url(url: str) -> str | None:
        path = urlparse(url).path
        name = Path(path).name
        return name or None

    @staticmethod
    def _ensure_fal_key_available() -> None:
        fal_key = os.getenv("FAL_KEY")
        if not fal_key:
            compatible_key = os.getenv("FAI_AI_API_KEY")
            if compatible_key:
                os.environ["FAL_KEY"] = compatible_key
                fal_key = compatible_key
        if not fal_key:
            msg = "Missing fal API key. Set FAL_KEY or FAI_AI_API_KEY in environment."
            raise ImageAnalysisError(msg)

    @staticmethod
    def _extract_detection_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidate_keys = ("detections", "objects", "predictions", "results")
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
            if (
                key == "results"
                and isinstance(value, dict)
                and isinstance(value.get("bboxes"), list)
                and all(isinstance(item, dict) for item in value["bboxes"])
            ):
                return value["bboxes"]
        return []
