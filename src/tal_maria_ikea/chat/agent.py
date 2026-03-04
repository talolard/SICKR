"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from tal_maria_ikea.chat.graph import (
    ChatGraphDeps,
    ChatGraphState,
    ParseUserIntentNode,
    build_chat_graph,
)
from tal_maria_ikea.config import get_settings

CHAT_AGENT_INSTRUCTIONS = (
    "You are an IKEA shopping assistant. Always call the run_search_graph tool exactly once "
    "with the user's message, then return the tool result without adding facts outside it."
)


def build_chat_agent() -> Agent[ChatGraphDeps, str]:
    """Build the web-chat agent that proxies user requests into the graph."""

    settings = get_settings()
    api_key = settings.gemini_api_key or os.getenv("GOOGLE_API_KEY")
    model = GoogleModel(
        settings.gemini_generation_model, provider=GoogleProvider(api_key=api_key)
    )
    agent = Agent[ChatGraphDeps, str](
        model=model,
        deps_type=ChatGraphDeps,
        instructions=CHAT_AGENT_INSTRUCTIONS,
        output_type=str,
    )

    @agent.tool
    def run_search_graph(ctx: RunContext[ChatGraphDeps], user_message: str) -> str:
        """Run the search graph once and return the refined response text."""

        graph = build_chat_graph()
        result = graph.run_sync(
            ParseUserIntentNode(user_message=user_message),
            state=ChatGraphState(),
            deps=ctx.deps,
        )
        return result.output.answer_text

    return agent
