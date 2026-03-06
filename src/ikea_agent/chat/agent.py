"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, BinaryContent, ModelRetry, RunContext, ToolReturn
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from ikea_agent.chat.search_diversity import diversify_results
from ikea_agent.config import get_settings
from ikea_agent.shared.types import (
    AttachmentRef,
    ImageToolOutput,
    RetrievalFilters,
    SearchGraphToolResult,
)
from ikea_agent.tools.floorplanner.models import (
    FloorPlannerValidationError,
    FloorPlanRenderRequest,
    scene_to_summary,
)
from ikea_agent.tools.floorplanner.tool import (
    render_floor_plan as run_floor_planner,
)
from ikea_agent.tools.floorplanner.yaml_codec import dump_scene_yaml, parse_scene_yaml
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
For first-pass confirmation, use a baseline scene with architecture + major furniture.
After baseline confirmation, use `render_floor_plan` changes to add detailed items (fixtures,
wall-mounted items, elevated/stacked placements).
Use `load_floor_plan_scene_yaml` to import user-provided YAML into typed scene state.
Use `export_floor_plan_scene_yaml` when user asks to save/export current scene.
If `render_floor_plan` fails, fix arguments and retry up to two times,
then ask for clarification.
After rendering a floor plan, ask the user to confirm whether it matches their room.
"""


def agent_instructions() -> str:
    """Return extended agent behavior instructions used for chat runs."""

    return """Bundle of Ikea products that will meet their needs.

    Users might give you a vague request like
    "Plants that grow in the dark corners of my apartment" or a detailed request like
    "I want to decorate my child's room which is AxY cm and has a large elevated bed and
    a north facing window. We need solutions for order, lighting and play, making it feel
    spacious. Find me solutions that keep the closet under the bed."

    Your persona is highly analytical and systematic. For every user query, deeply parse
    and deconstruct the user's intent, referencing and explicitly discussing relevant design
    principles and concepts (such as spatial efficiency, color theory, or biophilic design)
    as you break down the problem into individual needs.

    For each need or concept, generate and run a wide and diverse array of queries,
    including multiple phrasings and variations, both semantic and exact-match forms.
    For example, for low light plants, you should try: "low light house plants,"
    "plants for dark places," "shade tolerant indoor plants," etc., with added
    constraints for dimensions or price as relevant. Aim for broad and comprehensive
    search coverage; err on the side of including more variations and query approaches
    for each concept.

    You receive response objects from semantic search in the following format:

    class SearchGraphToolResult:
        results: list[ShortRetrievalResult]
        warning: SearchResultDiversityWarning | None
        total_candidates: int
        returned_count: int

    class ShortRetrievalResult:
        product_id: str
        product_name: str
        product_type: str | None
        description_text: str | None
        main_category: str | None
        sub_category: str | None
        width_cm: float | None
        depth_cm: float | None
        height_cm: float | None
        price_eur: float | None

    If `warning` is present, results are still valid but highly concentrated in one family.
    When that happens, run additional search queries or apply filters before final recommendations.

    Break down what the user needs, execute multiple diverse semantic queries for
    each need, and maximize coverage using query variation.

    From the results, select the ideal bundle of items and explain your recommendations
    in a systematic, analytical style, referencing the specific design principles or
    optimization concepts applied. Suggest unconventional, creative, or off-the-wall
    usages of Ikea items where they could provide an innovative or optimal solution
    for the user's needs.

    For each query you run, notify the user what you searched for and how many results you got back.

    Guide the user through the specific design principles you applied, tradeoffs made,
    and your analytical reasoning.

    For follow-up questions, always respond analytically, anchored in the products
    you found and based on deep understanding of the user's needs.

    At the end, provide an itemized list in table format, with item, description,
    reason, price, quantity, use canonical_product_key as the product id, and
    explicitly include the product's measurements (width, depth, and height from
    the search results) in the table. Verify and ensure that selected products'
    measurements fit into the intended placement in the room when creating your
    recommendations. Present multiple tables if there are distinct subbundles.

    If room layouts are provided (including yaml layout descriptions, specifications
    of axes, coordinates, and explicit measurement systems), use those to assign and
    present approximate coordinates for each item in the user's coordinate system,
    based on item and room dimensions. When suggesting locations, ensure that the
    product measurements match the available space.

    Only suggest items from search results. You may use the search tool repeatedly
    with variants to find the right items, but do not suggest items that were not in
    search results. Always ground your suggestions in the search results and the user's
    needs, and avoid making assumptions or suggesting items that were not surfaced
    in search results.
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


def build_chat_agent() -> Agent[ChatAgentDeps, str]:  # noqa: C901, PLR0915
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
    agent.instructions(agent_instructions)

    def _telemetry_context(ctx: RunContext[ChatAgentDeps]) -> dict[str, str | None]:
        return {
            "session_id": ctx.deps.state.session_id,
            "branch_from_session_id": ctx.deps.state.branch_from_session_id,
        }

    @agent.tool
    async def run_search_graph(
        ctx: RunContext[ChatAgentDeps],
        semantic_query: str,
        limit: int = 20,
        candidate_pool_limit: int | None = None,
        filters: RetrievalFilters | None = None,
    ) -> SearchGraphToolResult:
        """Run semantic search, diversify repetitive families, and return typed results."""

        target_pool_limit = candidate_pool_limit
        if target_pool_limit is not None:
            target_pool_limit = max(limit, min(500, target_pool_limit))
        graph = build_chat_graph()
        result = await graph.run(
            ParseUserIntentNode(user_message=semantic_query, result_limit=target_pool_limit),
            state=ChatGraphState(filters=filters),
            deps=ChatGraphDeps(runtime=ctx.deps.runtime),
        )
        diversified = diversify_results(
            results=result.output.product_matches,
            limit=limit,
        )
        logger.info(
            "graph_query_completed",
            extra={
                "query_text": semantic_query,
                "result_count": len(result.output.product_matches),
                "returned_result_count": len(diversified.results),
                "dominance_warning": (
                    diversified.warning.dominant_family if diversified.warning else None
                ),
                **_telemetry_context(ctx),
            },
        )
        return SearchGraphToolResult(
            results=diversified.results,
            warning=diversified.warning,
            total_candidates=len(result.output.product_matches),
            returned_count=len(diversified.results),
        )

    @agent.tool
    async def list_uploaded_images(ctx: RunContext[ChatAgentDeps]) -> list[AttachmentRef]:
        """List uploaded images from AG-UI shared state."""

        logger.info(
            "list_uploaded_images",
            extra={
                "attachment_count": len(ctx.deps.state.attachments),
                **_telemetry_context(ctx),
            },
        )
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

    @agent.tool
    def render_floor_plan(
        ctx: RunContext[ChatAgentDeps],
        request: FloorPlanRenderRequest,
    ) -> dict[str, object] | ToolReturn:
        """Render and/or update the active floor-plan scene with SVG+PNG outputs."""

        snapshot = ctx.deps.floor_plan_scene_store.get(ctx.deps.state.session_id)
        current_scene = snapshot.scene if snapshot is not None else None
        next_revision = 1 if snapshot is None else snapshot.revision + 1

        try:
            scene, output, _tool_return = run_floor_planner(
                request,
                scene_revision=next_revision,
                current_scene=current_scene,
            )
        except (FloorPlannerValidationError, ValueError) as exc:
            logger.exception(
                "render_floor_plan_failed",
                extra=_telemetry_context(ctx),
            )
            raise ModelRetry(
                "render_floor_plan failed. Correct the `scene`/`changes` payload "
                "(architecture/openings/placement ids/coordinates) and retry. "
                f"Error: {exc}"
            ) from exc

        output_png_path = Path(output.output_png_path)
        output_svg_path = Path(output.output_svg_path)
        if not output_png_path.exists() or not output_svg_path.exists():
            raise ModelRetry("render_floor_plan produced missing output artifacts.")

        stored_png = ctx.deps.attachment_store.save_image_bytes(
            content=output_png_path.read_bytes(),
            mime_type="image/png",
            filename="floor-plan.png",
        )
        stored_svg = ctx.deps.attachment_store.save_image_bytes(
            content=output_svg_path.read_bytes(),
            mime_type="image/svg+xml",
            filename="floor-plan.svg",
        )
        persisted = ctx.deps.floor_plan_scene_store.set(ctx.deps.state.session_id, scene)
        summary = scene_to_summary(scene)
        payload: dict[str, object] = {
            "caption": output.caption,
            "images": [stored_svg.ref, stored_png.ref],
            "scene_revision": persisted.revision,
            "scene_level": output.scene_level,
            "warnings": [warning.model_dump(mode="json") for warning in output.warnings],
            "legend_items": output.legend_items,
            "scale_major_step_cm": output.scale_major_step_cm,
            "scene_summary": summary,
            "scene": scene.model_dump(mode="json"),
        }
        logger.info(
            "render_floor_plan_completed",
            extra={
                "output_attachment_id": stored_png.ref.attachment_id,
                "scene_revision": persisted.revision,
                "wall_count": summary["wall_count"],
                "door_count": summary["door_count"],
                "window_count": summary["window_count"],
                "placement_count": summary["placement_count"],
                **_telemetry_context(ctx),
            },
        )
        if request.include_image_bytes:
            return ToolReturn(
                return_value=payload,
                content=[
                    BinaryContent(
                        data=output_png_path.read_bytes(),
                        media_type="image/png",
                    )
                ],
                metadata={
                    "scene_revision": persisted.revision,
                    "attachment_ids": [
                        stored_svg.ref.attachment_id,
                        stored_png.ref.attachment_id,
                    ],
                },
            )
        return payload

    @agent.tool
    def load_floor_plan_scene_yaml(
        ctx: RunContext[ChatAgentDeps],
        yaml_text: str,
        scene_level: Literal["baseline", "detailed"] = "detailed",
    ) -> dict[str, object]:
        """Load YAML into typed floor-plan scene state for iterative rendering."""

        scene = parse_scene_yaml(yaml_text, scene_level=scene_level)
        snapshot = ctx.deps.floor_plan_scene_store.set(ctx.deps.state.session_id, scene)
        summary = scene_to_summary(scene)
        return {
            "message": "Loaded floor-plan scene YAML into session state.",
            "scene_revision": snapshot.revision,
            "scene_level": scene.scene_level,
            "scene_summary": summary,
        }

    @agent.tool
    def export_floor_plan_scene_yaml(ctx: RunContext[ChatAgentDeps]) -> dict[str, object]:
        """Export current typed floor-plan scene state to YAML text."""

        snapshot = ctx.deps.floor_plan_scene_store.get(ctx.deps.state.session_id)
        if snapshot is None:
            raise ValueError("No floor-plan scene is loaded for this session.")
        return {
            "scene_revision": snapshot.revision,
            "yaml": dump_scene_yaml(snapshot.scene),
            "scene_summary": scene_to_summary(snapshot.scene),
        }

    @agent.tool
    async def detect_objects_in_image(
        ctx: RunContext[ChatAgentDeps],
        request: ObjectDetectionRequest,
    ) -> ObjectDetectionToolResult:
        """Detect objects in one uploaded image using Florence object detection."""

        logger.info(
            "detect_objects_in_image_start",
            extra=_telemetry_context(ctx),
        )
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

        logger.info(
            "estimate_depth_map_start",
            extra=_telemetry_context(ctx),
        )
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

        logger.info(
            "segment_image_with_prompt_start",
            extra=_telemetry_context(ctx),
        )
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

        logger.info(
            "analyze_room_photo_start",
            extra=_telemetry_context(ctx),
        )
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
