"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os
from logging import getLogger

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, RunContext
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

logger = getLogger(__name__)

CHAT_AGENT_INSTRUCTIONS = """You are an expert IKEA product assistant.

Use the `run_search_graph` tool to discover products relevant to the user query.
You may call the tool multiple times with different phrasings and filters.
Only recommend products that appear in tool results.
When recommending products, explain why each is suitable and include key dimensions and price.
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
    def run_search_graph(
        ctx: RunContext[ChatGraphDeps],
        semantic_query: str,
        limit: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[ShortRetrievalResult]:
        """Run semantic product search and return short product records."""

        graph = build_chat_graph()
        result = graph.run_sync(
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

    return agent
