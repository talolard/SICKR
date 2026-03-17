"""Local toolset for image-analysis agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from logging import getLogger

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.shared import (
    analysis_repository,
    build_remember_preference_tool,
    telemetry_context,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.persistence.analysis_repository import AnalysisRepository
from ikea_agent.tools.image_analysis import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    SegmentationRequest,
    SegmentationToolResult,
)
from ikea_agent.tools.image_analysis import analyze_room_photo as run_room_photo_analysis
from ikea_agent.tools.image_analysis import detect_objects_in_image as run_object_detection
from ikea_agent.tools.image_analysis import estimate_depth_map as run_depth_estimation
from ikea_agent.tools.image_analysis import (
    get_room_detail_details_from_photo as run_room_detail_details_from_photo,
)
from ikea_agent.tools.image_analysis import segment_image_with_prompt as run_image_segmentation

logger = getLogger(__name__)

TOOL_NAMES: tuple[str, ...] = (
    "remember_preference",
    "list_uploaded_images",
    "detect_objects_in_image",
    "estimate_depth_map",
    "segment_image_with_prompt",
    "analyze_room_photo",
    "get_room_detail_details_from_photo",
)

AnalysisRepositoryFactory = Callable[[ChatRuntime], AnalysisRepository | None]
ObjectDetectionRunner = Callable[..., Awaitable[ObjectDetectionToolResult]]
DepthEstimationRunner = Callable[..., Awaitable[DepthEstimationToolResult]]
SegmentationRunner = Callable[..., Awaitable[SegmentationToolResult]]
RoomPhotoAnalysisRunner = Callable[..., Awaitable[RoomPhotoAnalysisToolResult]]
RoomDetailAnalysisRunner = Callable[..., Awaitable[RoomDetailDetailsFromPhotoResult]]


@dataclass(frozen=True, slots=True)
class ImageAnalysisToolsetServices:
    """Service seams for image-analysis tools."""

    get_analysis_repository: AnalysisRepositoryFactory
    detect_objects_in_image: ObjectDetectionRunner
    estimate_depth_map: DepthEstimationRunner
    segment_image_with_prompt: SegmentationRunner
    analyze_room_photo: RoomPhotoAnalysisRunner
    get_room_detail_details_from_photo: RoomDetailAnalysisRunner


def default_image_analysis_toolset_services() -> ImageAnalysisToolsetServices:
    """Return the current default service bindings for image-analysis tools."""

    return ImageAnalysisToolsetServices(
        get_analysis_repository=analysis_repository,
        detect_objects_in_image=run_object_detection,
        estimate_depth_map=run_depth_estimation,
        segment_image_with_prompt=run_image_segmentation,
        analyze_room_photo=run_room_photo_analysis,
        get_room_detail_details_from_photo=run_room_detail_details_from_photo,
    )


def list_uploaded_images(ctx: RunContext[ImageAnalysisAgentDeps]) -> list[dict[str, object]]:
    """List uploaded images from AG-UI state."""

    logger.info(
        "list_uploaded_images",
        extra={
            "attachment_count": len(ctx.deps.state.attachments),
            **telemetry_context(ctx.deps.state),
        },
    )
    return [asdict(attachment) for attachment in ctx.deps.state.attachments]


async def _detect_objects_in_image_with_services(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: ObjectDetectionRequest,
    *,
    services: ImageAnalysisToolsetServices,
) -> ObjectDetectionToolResult:
    logger.info("detect_objects_in_image_start", extra=telemetry_context(ctx.deps.state))
    result = await services.detect_objects_in_image(
        request=request,
        attachment_store=ctx.deps.attachment_store,
    )
    repository = services.get_analysis_repository(ctx.deps.runtime)
    if repository is not None:
        repository.record_analysis(
            tool_name="detect_objects_in_image",
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            input_asset_id=request.image.attachment_id,
            request_json=request.model_dump(mode="json"),
            result_json=result.model_dump(mode="json"),
            detections=result.detections,
        )
    return result


async def detect_objects_in_image(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: ObjectDetectionRequest,
) -> ObjectDetectionToolResult:
    """Detect objects in one uploaded image using Florence object detection."""

    return await _detect_objects_in_image_with_services(
        ctx,
        request,
        services=default_image_analysis_toolset_services(),
    )


async def _estimate_depth_map_with_services(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: DepthEstimationRequest,
    *,
    services: ImageAnalysisToolsetServices,
) -> DepthEstimationToolResult:
    logger.info("estimate_depth_map_start", extra=telemetry_context(ctx.deps.state))
    result = await services.estimate_depth_map(
        request=request,
        attachment_store=ctx.deps.attachment_store,
    )
    repository = services.get_analysis_repository(ctx.deps.runtime)
    if repository is not None:
        repository.record_analysis(
            tool_name="estimate_depth_map",
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            input_asset_id=request.image.attachment_id,
            request_json=request.model_dump(mode="json"),
            result_json=result.model_dump(mode="json"),
            detections=[],
        )
    return result


async def estimate_depth_map(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: DepthEstimationRequest,
) -> DepthEstimationToolResult:
    """Estimate a relative depth map for one uploaded image using Marigold."""

    return await _estimate_depth_map_with_services(
        ctx,
        request,
        services=default_image_analysis_toolset_services(),
    )


async def _segment_image_with_prompt_with_services(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: SegmentationRequest,
    *,
    services: ImageAnalysisToolsetServices,
) -> SegmentationToolResult:
    logger.info("segment_image_with_prompt_start", extra=telemetry_context(ctx.deps.state))
    result = await services.segment_image_with_prompt(
        request=request,
        attachment_store=ctx.deps.attachment_store,
    )
    repository = services.get_analysis_repository(ctx.deps.runtime)
    if repository is not None:
        analysis_id = repository.record_analysis(
            tool_name="segment_image_with_prompt",
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            input_asset_id=request.image.attachment_id,
            request_json=request.model_dump(mode="json"),
            result_json=result.model_dump(mode="json"),
            detections=[],
        )
        if analysis_id is not None:
            result = result.model_copy(update={"analysis_id": analysis_id})
    return result


async def segment_image_with_prompt(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: SegmentationRequest,
) -> SegmentationToolResult:
    """Create prompt-driven segmentation masks for one uploaded image using SAM."""

    return await _segment_image_with_prompt_with_services(
        ctx,
        request,
        services=default_image_analysis_toolset_services(),
    )


async def _analyze_room_photo_with_services(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: RoomPhotoAnalysisRequest | None = None,
    *,
    services: ImageAnalysisToolsetServices,
) -> RoomPhotoAnalysisToolResult:
    logger.info("analyze_room_photo_start", extra=telemetry_context(ctx.deps.state))
    resolved_request = request
    if resolved_request is None:
        if not ctx.deps.state.attachments:
            raise ValueError("No uploaded images available. Upload a room photo first.")
        resolved_request = RoomPhotoAnalysisRequest(
            image=AttachmentRefPayload.from_ref(ctx.deps.state.attachments[0])
        )

    result = await services.analyze_room_photo(
        request=resolved_request,
        attachment_store=ctx.deps.attachment_store,
    )
    repository = services.get_analysis_repository(ctx.deps.runtime)
    if repository is not None:
        detections = result.object_detection.detections if result.object_detection else []
        repository.record_analysis(
            tool_name="analyze_room_photo",
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            input_asset_id=resolved_request.image.attachment_id,
            request_json=resolved_request.model_dump(mode="json"),
            result_json=result.model_dump(mode="json"),
            detections=detections,
        )
    return result


async def analyze_room_photo(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: RoomPhotoAnalysisRequest | None = None,
) -> RoomPhotoAnalysisToolResult:
    """Run combined room-photo understanding (object detection + depth)."""

    return await _analyze_room_photo_with_services(
        ctx,
        request,
        services=default_image_analysis_toolset_services(),
    )


async def _get_room_detail_details_from_photo_with_services(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: RoomDetailDetailsFromPhotoRequest | None = None,
    *,
    services: ImageAnalysisToolsetServices,
) -> RoomDetailDetailsFromPhotoResult:
    logger.info(
        "get_room_detail_details_from_photo_start",
        extra=telemetry_context(ctx.deps.state),
    )
    resolved_request = request
    if resolved_request is None:
        if not ctx.deps.state.attachments:
            raise ValueError("No uploaded images available. Upload room photos first.")
        resolved_request = RoomDetailDetailsFromPhotoRequest(
            images=[
                AttachmentRefPayload.from_ref(attachment)
                for attachment in ctx.deps.state.attachments
            ]
        )

    result = await services.get_room_detail_details_from_photo(
        request=resolved_request,
        attachment_store=ctx.deps.attachment_store,
    )
    repository = services.get_analysis_repository(ctx.deps.runtime)
    if repository is not None:
        repository.record_analysis(
            tool_name="get_room_detail_details_from_photo",
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            input_asset_id=resolved_request.images[0].attachment_id,
            input_asset_ids=[image.attachment_id for image in resolved_request.images],
            request_json=resolved_request.model_dump(mode="json"),
            result_json=result.model_dump(mode="json"),
            detections=[],
        )
    logger.info(
        "get_room_detail_details_from_photo_complete",
        extra={
            "image_count": len(resolved_request.images),
            "room_type": result.room_type,
            "cross_image_room_relationship": result.cross_image_room_relationship,
            **telemetry_context(ctx.deps.state),
        },
    )
    return result


async def get_room_detail_details_from_photo(
    ctx: RunContext[ImageAnalysisAgentDeps],
    request: RoomDetailDetailsFromPhotoRequest | None = None,
) -> RoomDetailDetailsFromPhotoResult:
    """Extract room-detail observations across one or more uploaded room photos."""

    return await _get_room_detail_details_from_photo_with_services(
        ctx,
        request,
        services=default_image_analysis_toolset_services(),
    )


def build_image_analysis_toolset(
    services: ImageAnalysisToolsetServices | None = None,
) -> FunctionToolset[ImageAnalysisAgentDeps]:
    """Build toolset for image-analysis agent."""

    resolved_services = services or default_image_analysis_toolset_services()

    async def detect_objects_in_image_tool(
        ctx: RunContext[ImageAnalysisAgentDeps],
        request: ObjectDetectionRequest,
    ) -> ObjectDetectionToolResult:
        return await _detect_objects_in_image_with_services(
            ctx,
            request,
            services=resolved_services,
        )

    async def estimate_depth_map_tool(
        ctx: RunContext[ImageAnalysisAgentDeps],
        request: DepthEstimationRequest,
    ) -> DepthEstimationToolResult:
        return await _estimate_depth_map_with_services(
            ctx,
            request,
            services=resolved_services,
        )

    async def segment_image_with_prompt_tool(
        ctx: RunContext[ImageAnalysisAgentDeps],
        request: SegmentationRequest,
    ) -> SegmentationToolResult:
        return await _segment_image_with_prompt_with_services(
            ctx,
            request,
            services=resolved_services,
        )

    async def analyze_room_photo_tool(
        ctx: RunContext[ImageAnalysisAgentDeps],
        request: RoomPhotoAnalysisRequest | None = None,
    ) -> RoomPhotoAnalysisToolResult:
        return await _analyze_room_photo_with_services(
            ctx,
            request,
            services=resolved_services,
        )

    async def get_room_detail_details_from_photo_tool(
        ctx: RunContext[ImageAnalysisAgentDeps],
        request: RoomDetailDetailsFromPhotoRequest | None = None,
    ) -> RoomDetailDetailsFromPhotoResult:
        return await _get_room_detail_details_from_photo_with_services(
            ctx,
            request,
            services=resolved_services,
        )

    return FunctionToolset(
        tools=[
            build_remember_preference_tool(),
            Tool(list_uploaded_images, name="list_uploaded_images"),
            Tool(detect_objects_in_image_tool, name="detect_objects_in_image"),
            Tool(estimate_depth_map_tool, name="estimate_depth_map"),
            Tool(segment_image_with_prompt_tool, name="segment_image_with_prompt"),
            Tool(analyze_room_photo_tool, name="analyze_room_photo"),
            Tool(
                get_room_detail_details_from_photo_tool,
                name="get_room_detail_details_from_photo",
            ),
        ]
    )
