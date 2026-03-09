"""PydanticAI agent wrapper that delegates product questions to the chat graph."""

from __future__ import annotations

import os
from pathlib import Path

from google.genai.types import ThinkingLevel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings, ThinkingConfigDict
from pydantic_ai.providers.google import GoogleProvider

from ikea_agent.chat.deps import ChatAgentDeps, Room3DSnapshotContext
from ikea_agent.chat.tools import (
    build_room_3d_snapshot_context_payload as _build_room_3d_snapshot_context_payload,
)
from ikea_agent.chat.tools import (
    register_floor_plan_tools,
    register_image_analysis_tools,
    register_search_context_tools,
)
from ikea_agent.config import get_settings
from ikea_agent.persistence.room_3d_repository import Room3DSnapshotEntry

_INSTRUCTIONS_PATH = Path(__file__).with_name("agent_instructions.md")


def _load_instructions() -> str:
    """Load agent instructions from the co-located markdown file.

    Strips the YAML front-matter (delimited by ``---``) so only the
    instruction body reaches the model.
    """

    raw = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            raw = raw[end + 3 :].lstrip("\n")
    return raw.strip()


# build_room_3d_snapshot_context_payload is re-exported from chat.tools so
# tests and callers can continue importing it from ikea_agent.chat.agent.
def build_room_3d_snapshot_context_payload(
    *,
    state_snapshots: list[Room3DSnapshotContext],
    persisted_snapshots: list[Room3DSnapshotEntry],
) -> dict[str, object]:
    """Backwards-compatible wrapper for the shared 3D snapshot payload helper."""

    return _build_room_3d_snapshot_context_payload(
        state_snapshots=state_snapshots,
        persisted_snapshots=persisted_snapshots,
    )


def build_chat_agent() -> Agent[ChatAgentDeps, str]:
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
        instructions=_load_instructions(),
        output_type=str,
    )

    register_search_context_tools(agent)
    register_floor_plan_tools(agent)
    register_image_analysis_tools(agent)

    return agent
