"""Image-analysis tool registrations for the chat agent."""

from __future__ import annotations

from logging import getLogger

from pydantic_ai import Agent, RunContext

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.tools.support import analysis_repository, telemetry_context
from ikea_agent.tools.image_analysis import (
    AttachmentRefPayload,
    DepthEstimationRequest,
    DepthEstimationToolResult,
    ObjectDetectionRequest,
    ObjectDetectionToolResult,
    RoomPhotoAnalysisRequest,
    RoomPhotoAnalysisToolResult,
    SegmentationRequest,
    SegmentationToolResult,
)
from ikea_agent.tools.image_analysis import analyze_room_photo as run_room_photo_analysis
from ikea_agent.tools.image_analysis import detect_objects_in_image as run_object_detection
from ikea_agent.tools.image_analysis import estimate_depth_map as run_depth_estimation
from ikea_agent.tools.image_analysis import segment_image_with_prompt as run_image_segmentation

logger = getLogger(__name__)


def register_image_analysis_tools(agent: Agent[ChatAgentDeps, str]) -> None:  # noqa: C901
    """Register image-analysis tools on the chat agent."""

    @agent.tool
    async def detect_objects_in_image(
        ctx: RunContext[ChatAgentDeps],
        request: ObjectDetectionRequest,
    ) -> ObjectDetectionToolResult:
        """Detect objects in one uploaded image using Florence object detection."""

        logger.info(
            "detect_objects_in_image_start",
            extra=telemetry_context(ctx),
        )
        result = await run_object_detection(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )
        repository = analysis_repository(ctx)
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

    @agent.tool
    async def estimate_depth_map(
        ctx: RunContext[ChatAgentDeps],
        request: DepthEstimationRequest,
    ) -> DepthEstimationToolResult:
        """Estimate a relative depth map for one uploaded image using Marigold."""

        logger.info(
            "estimate_depth_map_start",
            extra=telemetry_context(ctx),
        )
        result = await run_depth_estimation(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )
        repository = analysis_repository(ctx)
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

    @agent.tool
    async def segment_image_with_prompt(
        ctx: RunContext[ChatAgentDeps],
        request: SegmentationRequest,
    ) -> SegmentationToolResult:
        """Create prompt-driven segmentation masks for one uploaded image using SAM."""

        logger.info(
            "segment_image_with_prompt_start",
            extra=telemetry_context(ctx),
        )
        result = await run_image_segmentation(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )
        repository = analysis_repository(ctx)
        if repository is not None:
            repository.record_analysis(
                tool_name="segment_image_with_prompt",
                thread_id=ctx.deps.state.thread_id or "anonymous-thread",
                run_id=ctx.deps.state.run_id,
                input_asset_id=request.image.attachment_id,
                request_json=request.model_dump(mode="json"),
                result_json=result.model_dump(mode="json"),
                detections=[],
            )
        return result

    @agent.tool
    async def analyze_room_photo(
        ctx: RunContext[ChatAgentDeps],
        request: RoomPhotoAnalysisRequest | None = None,
    ) -> RoomPhotoAnalysisToolResult:
        """Run combined room-photo understanding (object detection + depth)."""

        logger.info(
            "analyze_room_photo_start",
            extra=telemetry_context(ctx),
        )
        resolved_request = request
        if resolved_request is None:
            if not ctx.deps.state.attachments:
                raise ValueError("No uploaded images available. Upload a room photo first.")
            resolved_request = RoomPhotoAnalysisRequest(
                image=AttachmentRefPayload.from_ref(ctx.deps.state.attachments[0])
            )

        result = await run_room_photo_analysis(
            request=resolved_request,
            attachment_store=ctx.deps.attachment_store,
        )
        repository = analysis_repository(ctx)
        if repository is not None:
            detections = (
                result.object_detection.detections if result.object_detection is not None else []
            )
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
