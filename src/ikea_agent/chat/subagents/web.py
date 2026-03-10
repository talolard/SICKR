"""PydanticAI web adapters for graph-based subagents."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ikea_agent.chat.subagents.registry import available_subagents, get_subagent


def list_subagent_catalog() -> list[dict[str, str]]:
    """Return registered subagents with stable web path metadata."""

    return [
        {
            "name": entry.name,
            "description": entry.description,
            "web_path": f"/subagents/{entry.name}/chat/",
        }
        for entry in available_subagents()
    ]


def build_subagent_web_agent(subagent_name: str) -> Agent[None, str]:
    """Build a lightweight web-chat adapter around one registered subagent runner."""

    registration = get_subagent(subagent_name)
    model = FunctionModel(
        _build_subagent_function(registration.run),
        model_name=f"subagent_{subagent_name}",
    )
    return Agent[None, str](
        model=model,
        deps_type=type(None),
        output_type=str,
        instructions=(
            "You are a chat wrapper for a graph-based subagent. "
            "For each turn, use the latest user message and return the subagent assistant message."
        ),
    )


def _build_subagent_function(
    runner: Callable[[str], Awaitable[dict[str, object]]],
) -> Callable[[list[ModelMessage], AgentInfo], Awaitable[ModelResponse]]:
    async def _run(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        _ = info
        user_message = _latest_user_prompt_text(messages)
        raw_input = json.dumps({"user_message": user_message}, ensure_ascii=True)
        result = await runner(raw_input)
        assistant_text = _extract_assistant_message(result)
        return ModelResponse(
            parts=[TextPart(content=assistant_text)],
            model_name="subagent-wrapper",
        )

    return _run


def _latest_user_prompt_text(messages: list[ModelMessage]) -> str:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        content = _first_user_prompt_content(message.parts)
        if content is not None and content.strip():
            return content
    return ""


def _first_user_prompt_content(parts: Sequence[ModelRequestPart]) -> str | None:
    for part in parts:
        if isinstance(part, UserPromptPart):
            if isinstance(part.content, str):
                return part.content
            fragments = [item for item in part.content if isinstance(item, str)]
            return "\n".join(fragments)
    return None


def _extract_assistant_message(result: object) -> str:
    if isinstance(result, dict):
        value = result.get("assistant_message")
        if isinstance(value, str) and value.strip():
            return value
    return "Subagent returned no assistant message for this turn."
