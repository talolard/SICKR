"""Agent-facing fal.ai tool wrappers for image analysis workflows."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.image_analysis.core import (
    FLORENCE_MODEL_ID,
    MARIGOLD_MODEL_ID,
    SAM_MODEL_ID,
    FalImageAnalysisCore,
    PreparedImage,
)
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    DepthEstimationOptions,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    DepthParametersUsed,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    SegmentationMask,
    SegmentationRequest,
    SegmentationToolResult,
)


class FalImageAnalysisService:
    """Thin orchestration layer around shared fal IO helpers and typed payloads."""

    def __init__(self, attachment_store: AttachmentStore) -> None:
        """Create service with one attachment repository dependency."""

        self._core = FalImageAnalysisCore(attachment_store)

    async def detect_objects_in_image(
        self,
        request: ObjectDetectionRequest,
        *,
        prepared: PreparedImage | None = None,
    ) -> ObjectDetectionToolResult:
        """Run Florence object detection and emit normalized detections + overlay."""

        prepared_image = prepared or await self._core.prepare_image(request.image)
        payload = await self._core.call_model(
            model_id=FLORENCE_MODEL_ID,
            arguments={"image_url": prepared_image.fal_image_url},
            start_timeout=15.0,
            client_timeout=60.0,
        )
        detections = self._core.parse_object_detections(
            payload,
            image_width=prepared_image.width,
            image_height=prepared_image.height,
        )
        output_images: list[AttachmentRefPayload] = []
        if request.include_overlay_image:
            output_images.append(
                self._core.create_detection_overlay(
                    prepared=prepared_image,
                    detections=detections,
                )
            )
        return ObjectDetectionToolResult(
            caption=(
                "Object detection completed. Treat detections as hints and ask user "
                "to confirm uncertain items."
            ),
            images=output_images,
            model_id=FLORENCE_MODEL_ID,
            image_width_px=prepared_image.width,
            image_height_px=prepared_image.height,
            detections=detections,
        )

    async def estimate_depth_map(
        self,
        request: DepthEstimationRequest,
        *,
        prepared: PreparedImage | None = None,
    ) -> DepthEstimationToolResult:
        """Run Marigold depth model and persist returned depth artifacts."""

        prepared_image = prepared or await self._core.prepare_image(request.image)
        payload = await self._core.call_model(
            model_id=MARIGOLD_MODEL_ID,
            arguments={
                "image_url": prepared_image.fal_image_url,
                "ensemble_size": request.ensemble_size,
                "processing_res": request.processing_res,
                "resample_method": request.resample_method,
                "seed": request.seed,
                "output_format": request.output_format,
            },
            start_timeout=30.0,
            client_timeout=180.0,
        )
        named_urls = self._extract_named_image_urls(payload)
        depth_url = named_urls.get("depth")
        visual_url = named_urls.get("visualization")
        if depth_url is None and visual_url is None:
            image_urls = self._core.parse_image_urls(payload)
            if image_urls:
                visual_url = image_urls[0]
                if len(image_urls) > 1:
                    depth_url = image_urls[1]

        depth_image = (
            await self._core.download_to_attachment(
                remote_url=depth_url,
                fallback_filename="depth-map.png",
            )
            if depth_url
            else None
        )
        visualization_image = (
            await self._core.download_to_attachment(
                remote_url=visual_url,
                fallback_filename="depth-visualization.png",
            )
            if visual_url
            else None
        )
        output_images: list[AttachmentRefPayload] = []
        if visualization_image is not None:
            output_images.append(visualization_image)
        if depth_image is not None:
            output_images.append(depth_image)
        return DepthEstimationToolResult(
            caption=(
                "Depth estimation completed. Depth map is relative and should not be "
                "treated as absolute centimeter distance without scale references."
            ),
            images=output_images,
            model_id=MARIGOLD_MODEL_ID,
            depth_image=depth_image,
            visualization_image=visualization_image,
            parameters_used=DepthParametersUsed(
                ensemble_size=request.ensemble_size,
                processing_res=request.processing_res,
                resample_method=request.resample_method,
                seed=request.seed,
                output_format=request.output_format,
            ),
        )

    async def segment_image_with_prompt(
        self,
        request: SegmentationRequest,
        *,
        prepared: PreparedImage | None = None,
    ) -> SegmentationToolResult:
        """Run prompt-driven SAM segmentation and persist mask artifacts."""

        prepared_image = prepared or await self._core.prepare_image(request.image)
        payload = await self._core.call_model(
            model_id=SAM_MODEL_ID,
            arguments={
                "image_url": prepared_image.fal_image_url,
                "prompt": request.prompt,
                "return_multiple_masks": request.return_multiple_masks,
                "mask_limit": request.mask_limit,
                "keep_model_loaded": request.keep_model_loaded,
            },
            start_timeout=30.0,
            client_timeout=180.0,
        )
        masks = await self._collect_masks_from_payload(payload=payload, limit=request.mask_limit)
        overlay = (
            self._core.create_segmentation_overlay(
                prepared=prepared_image,
                mask_images=[mask.mask_image for mask in masks],
            )
            if masks
            else None
        )

        output_images: list[AttachmentRefPayload] = [mask.mask_image for mask in masks]
        if overlay is not None:
            output_images.insert(0, overlay)

        return SegmentationToolResult(
            caption="Segmentation completed for the prompt. Review masks for false positives.",
            images=output_images,
            model_id=SAM_MODEL_ID,
            prompt=request.prompt,
            masks=masks,
            overlay_image=overlay,
        )

    async def analyze_room_photo(
        self, request: RoomPhotoAnalysisRequest
    ) -> RoomPhotoAnalysisToolResult:
        """Run combined object+depth analysis using one shared uploaded image URL."""

        prepared_image = await self._core.prepare_image(request.image)
        object_task = (
            self.detect_objects_in_image(
                ObjectDetectionRequest(
                    image=request.image,
                    include_overlay_image=request.object_detection.include_overlay_image,
                ),
                prepared=prepared_image,
            )
            if request.run_object_detection
            else None
        )
        depth_task = (
            self.estimate_depth_map(
                DepthEstimationRequest(
                    image=request.image,
                    ensemble_size=request.depth_estimation.ensemble_size,
                    processing_res=request.depth_estimation.processing_res,
                    resample_method=request.depth_estimation.resample_method,
                    seed=request.depth_estimation.seed,
                    output_format=request.depth_estimation.output_format,
                ),
                prepared=prepared_image,
            )
            if request.run_depth
            else None
        )
        gathered = await asyncio.gather(
            object_task if object_task is not None else self._none_async(),
            depth_task if depth_task is not None else self._none_async(),
        )
        object_result = gathered[0]
        depth_result = gathered[1]
        images: list[AttachmentRefPayload] = []
        hints: list[str] = []
        if isinstance(object_result, ObjectDetectionToolResult):
            images.extend(object_result.images[:1])
            if object_result.detections:
                top_labels = ", ".join(
                    detection.label for detection in object_result.detections[:5]
                )
                hints.append(f"Detected objects include: {top_labels}.")
            else:
                hints.append("Object detection returned no confident objects.")
        if isinstance(depth_result, DepthEstimationToolResult):
            images.extend(depth_result.images[:1])
            hints.append("Depth map generated for rough front-to-back structure checks.")
        if not hints:
            hints.append("No analysis was run. Enable object detection and/or depth estimation.")
        return RoomPhotoAnalysisToolResult(
            caption="Combined room photo analysis complete.",
            images=images,
            object_detection=object_result
            if isinstance(object_result, ObjectDetectionToolResult)
            else None,
            depth=depth_result if isinstance(depth_result, DepthEstimationToolResult) else None,
            room_hints=hints,
        )

    async def _collect_masks_from_payload(  # noqa: C901
        self,
        *,
        payload: dict[str, Any],
        limit: int,
    ) -> list[SegmentationMask]:
        mask_entries = payload.get("masks")
        masks: list[SegmentationMask] = []
        if isinstance(mask_entries, list):
            for index, entry in enumerate(mask_entries):
                if len(masks) >= limit:
                    break
                if isinstance(entry, Mapping):
                    mask_url = entry.get("url")
                    if isinstance(mask_url, str) and mask_url.startswith("http"):
                        mask_image = await self._core.download_to_attachment(
                            remote_url=mask_url,
                            fallback_filename=f"segmentation-mask-{index + 1}.png",
                        )
                        label = str(entry.get("label") or entry.get("name") or f"mask-{index + 1}")
                        masks.append(SegmentationMask(label=label, mask_image=mask_image))
                elif isinstance(entry, str) and entry.startswith("http"):
                    mask_image = await self._core.download_to_attachment(
                        remote_url=entry,
                        fallback_filename=f"segmentation-mask-{index + 1}.png",
                    )
                    masks.append(SegmentationMask(label=f"mask-{index + 1}", mask_image=mask_image))
        if masks:
            return masks

        for index, image_url in enumerate(self._core.parse_image_urls(payload)[:limit]):
            mask_image = await self._core.download_to_attachment(
                remote_url=image_url,
                fallback_filename=f"segmentation-mask-{index + 1}.png",
            )
            masks.append(SegmentationMask(label=f"mask-{index + 1}", mask_image=mask_image))
        return masks

    @staticmethod
    def _extract_named_image_urls(payload: dict[str, Any]) -> dict[str, str]:  # noqa: C901
        named_urls: dict[str, str] = {}
        stack: list[tuple[str, Any]] = [("", payload)]
        while stack:
            path, value = stack.pop()
            if isinstance(value, dict):
                for key, nested in value.items():
                    nested_path = f"{path}.{key}" if path else key
                    if key == "url" and isinstance(nested, str) and nested.startswith("http"):
                        lowered = path.lower()
                        if "depth" in lowered and "visual" not in lowered:
                            named_urls.setdefault("depth", nested)
                        elif "visual" in lowered:
                            named_urls.setdefault("visualization", nested)
                    else:
                        stack.append((nested_path, nested))
            elif isinstance(value, list):
                for index, nested in enumerate(value):
                    stack.append((f"{path}[{index}]", nested))
        return named_urls

    @staticmethod
    async def _none_async() -> None:
        return None


async def detect_objects_in_image(
    *,
    request: ObjectDetectionRequest,
    attachment_store: AttachmentStore,
) -> ObjectDetectionToolResult:
    """Tool wrapper for Florence object detection."""

    service = FalImageAnalysisService(attachment_store)
    return await service.detect_objects_in_image(request)


async def estimate_depth_map(
    *,
    request: DepthEstimationRequest,
    attachment_store: AttachmentStore,
) -> DepthEstimationToolResult:
    """Tool wrapper for Marigold depth estimation."""

    service = FalImageAnalysisService(attachment_store)
    return await service.estimate_depth_map(request)


async def segment_image_with_prompt(
    *,
    request: SegmentationRequest,
    attachment_store: AttachmentStore,
) -> SegmentationToolResult:
    """Tool wrapper for SAM prompt-driven segmentation."""

    service = FalImageAnalysisService(attachment_store)
    return await service.segment_image_with_prompt(request)


async def analyze_room_photo(
    *,
    request: RoomPhotoAnalysisRequest,
    attachment_store: AttachmentStore,
) -> RoomPhotoAnalysisToolResult:
    """Tool wrapper that combines object detection and depth estimation."""

    service = FalImageAnalysisService(attachment_store)
    return await service.analyze_room_photo(request)


def build_depth_request_from_options(
    *,
    image: AttachmentRefPayload,
    options: DepthEstimationOptions,
) -> DepthEstimationRequest:
    """Map combined-tool depth options into the standalone depth request model."""

    return DepthEstimationRequest(
        image=image,
        ensemble_size=options.ensemble_size,
        processing_res=options.processing_res,
        resample_method=options.resample_method,
        seed=options.seed,
        output_format=options.output_format,
    )
