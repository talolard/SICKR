"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os
from logging import getLogger

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, RunContext, ToolReturn
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from ikea_agent.config import get_settings
from ikea_agent.shared.types import RetrievalFilters, ShortRetrievalResult
from ikea_agent.tools.floorplanner.models import FloorPlanRequest
from ikea_agent.tools.floorplanner.tool import (
    FloorPlannerToolResult,
)
from ikea_agent.tools.floorplanner.tool import (
    render_floor_plan as run_floor_planner,
)

logger = getLogger(__name__)

CHAT_AGENT_INSTRUCTIONS = """You are an expert IKEA product assistant.

Use the `run_search_graph` tool to discover products relevant to the user query.
You may call the tool multiple times with different phrasings and filters.
Only recommend products that appear in tool results.
When recommending products, explain why each is suitable and include key dimensions and price.
Use `render_floor_plan` when the user provides enough room dimensions/openings to draft a layout.
After rendering a floor plan, ask the user to confirm whether it matches their room.
"""


def build_chat_agent() -> Agent[ChatGraphDeps, str]:
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
    agent = Agent[ChatGraphDeps, str](
        model=model,
        deps_type=ChatGraphDeps,
        instructions=CHAT_AGENT_INSTRUCTIONS,
        output_type=str,
    )

    @agent.tool
    async def run_search_graph(
        ctx: RunContext[ChatGraphDeps],
        semantic_query: str,
        limit: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[ShortRetrievalResult]:
        """Run semantic product search and return short product records."""

        graph = build_chat_graph()
        result = await graph.run(
            ParseUserIntentNode(user_message=semantic_query),
            state=ChatGraphState(filters=filters),
            deps=ctx.deps,
        )
        logger.info(
            "graph_query_completed",
            extra={
                "query_text": semantic_query,
                "result_count": len(result.output.product_matches),
            },
        )
        return result.output.product_matches[:limit]

    @agent.tool_plain
    def render_floor_plan(request: FloorPlanRequest) -> FloorPlannerToolResult | ToolReturn:
        """Render a floor plan image from typed centimeter inputs."""

        return run_floor_planner(request)

    return agent
