"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os
from logging import getLogger
from urllib.parse import quote

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, RunContext, ToolReturn
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from ikea_agent.config import get_settings
from ikea_agent.shared.types import (
    AttachmentRef,
    ImageToolOutput,
    RetrievalFilters,
    ShortRetrievalResult,
)
from ikea_agent.tools.floorplanner.models import FloorPlanRequest
from ikea_agent.tools.floorplanner.tool import (
    FloorPlannerToolResult,
)
from ikea_agent.tools.floorplanner.tool import (
    render_floor_plan as run_floor_planner,
)
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
from ikea_agent.tools.image_analysis import (
    analyze_room_photo as run_room_photo_analysis,
)
from ikea_agent.tools.image_analysis import (
    detect_objects_in_image as run_object_detection,
)
from ikea_agent.tools.image_analysis import (
    estimate_depth_map as run_depth_estimation,
)
from ikea_agent.tools.image_analysis import (
    segment_image_with_prompt as run_image_segmentation,
)

logger = getLogger(__name__)

CHAT_AGENT_INSTRUCTIONS = """You are an expert IKEA product assistant.

Use the `run_search_graph` tool to discover products relevant to the user query.
You may call the tool multiple times with different phrasings and filters.
Only recommend products that appear in tool results.
When recommending products, explain why each is suitable and include key dimensions and price.
If user references uploaded images, use `list_uploaded_images` to inspect what images are available.
Use `analyze_room_photo` when user uploads a room photo and asks for quick room understanding.
Use `detect_objects_in_image` when you need a detailed inventory of visible objects.
Use `estimate_depth_map` when rough depth structure can help reason about layout.
Use `segment_image_with_prompt` to find prompt-defined items (for example clutter, leaves).
Use `generate_floor_plan_preview_image` when the user asks to visualize a draft room layout.
Use `render_floor_plan` when the user provides enough room dimensions/openings to draft a layout.
After rendering a floor plan, ask the user to confirm whether it matches their room.
"""


def _preview_svg_data_uri() -> str:
    """Return deterministic SVG preview as a URL-safe data URI."""

    svg_text = """
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420">
  <rect x="20" y="20" width="600" height="380" fill="#f6f6f6" stroke="#333" />
  <rect x="80" y="80" width="180" height="120" fill="#d9e6ff" stroke="#1d4ed8" />
  <rect x="340" y="120" width="220" height="160" fill="#ffe4d6" stroke="#c2410c" />
  <text x="90" y="110" font-size="20" fill="#1f2937">Wardrobe</text>
  <text x="350" y="150" font-size="20" fill="#1f2937">Bed</text>
</svg>
""".strip()
    return f"data:image/svg+xml,{quote(svg_text)}"


def build_chat_agent() -> Agent[ChatAgentDeps, str]:  # noqa: C901
    """Build the web-chat agent that proxies user requests into the graph."""

    settings = get_settings()
    google_model_settings = GoogleModelSettings(
        google_thinking_config=ThinkingConfigDict(
            include_thoughts=True,
            thinking_level=ThinkingLevel.HIGH,
        )
    )
    api_key = settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")
    model = GoogleModel(
        settings.gemini_generation_model,
        settings=google_model_settings,
        provider=GoogleProvider(api_key=api_key),
    )
    agent = Agent[ChatAgentDeps, str](
        model=model,
        deps_type=ChatAgentDeps,
        instructions=CHAT_AGENT_INSTRUCTIONS,
        output_type=str,
    )

    @agent.tool
    async def run_search_graph(
        ctx: RunContext[ChatAgentDeps],
        semantic_query: str,
        limit: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[ShortRetrievalResult]:
        """Run semantic product search and return short product records."""

        graph = build_chat_graph()
        result = await graph.run(
            ParseUserIntentNode(user_message=semantic_query),
            state=ChatGraphState(filters=filters),
            deps=ChatGraphDeps(runtime=ctx.deps.runtime),
        )
        logger.info(
            "graph_query_completed",
            extra={
                "query_text": semantic_query,
                "result_count": len(result.output.product_matches),
            },
        )
        return result.output.product_matches[:limit]

    @agent.tool
    async def list_uploaded_images(ctx: RunContext[ChatAgentDeps]) -> list[AttachmentRef]:
        """List uploaded images from AG-UI shared state."""

        return ctx.deps.state.attachments

    @agent.tool_plain
    def generate_floor_plan_preview_image() -> ImageToolOutput:
        """Return a deterministic preview image the UI can render inline."""

        preview_ref = AttachmentRef(
            attachment_id="generated-floor-plan-preview",
            mime_type="image/svg+xml",
            uri=_preview_svg_data_uri(),
            width=640,
            height=420,
            file_name="generated-floor-plan-preview.svg",
        )
        return ImageToolOutput(
            caption="Draft floor plan preview generated from current assumptions.",
            images=[preview_ref],
        )

    @agent.tool_plain
    def render_floor_plan(request: FloorPlanRequest) -> FloorPlannerToolResult | ToolReturn:
        """Render a floor plan image from typed centimeter inputs."""

        return run_floor_planner(request)

    @agent.tool
    async def detect_objects_in_image(
        ctx: RunContext[ChatAgentDeps],
        request: ObjectDetectionRequest,
    ) -> ObjectDetectionToolResult:
        """Detect objects in one uploaded image using Florence object detection."""

        return await run_object_detection(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )

    @agent.tool
    async def estimate_depth_map(
        ctx: RunContext[ChatAgentDeps],
        request: DepthEstimationRequest,
    ) -> DepthEstimationToolResult:
        """Estimate a relative depth map for one uploaded image using Marigold."""

        return await run_depth_estimation(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )

    @agent.tool
    async def segment_image_with_prompt(
        ctx: RunContext[ChatAgentDeps],
        request: SegmentationRequest,
    ) -> SegmentationToolResult:
        """Create prompt-driven segmentation masks for one uploaded image using SAM."""

        return await run_image_segmentation(
            request=request,
            attachment_store=ctx.deps.attachment_store,
        )

    @agent.tool
    async def analyze_room_photo(
        ctx: RunContext[ChatAgentDeps],
        request: RoomPhotoAnalysisRequest | None = None,
    ) -> RoomPhotoAnalysisToolResult:
        """Run combined room-photo understanding (object detection + depth)."""

        resolved_request = request
        if resolved_request is None:
            if not ctx.deps.state.attachments:
                raise ValueError("No uploaded images available. Upload a room photo first.")
            resolved_request = RoomPhotoAnalysisRequest(
                image=AttachmentRefPayload.from_ref(ctx.deps.state.attachments[0])
            )

        return await run_room_photo_analysis(
            request=resolved_request,
            attachment_store=ctx.deps.attachment_store,
        )

    return agent
