"""Helpers for rendering canonical PydanticAI history back into AG-UI messages."""

from __future__ import annotations

import json
from base64 import b64encode
from collections.abc import Callable, Sequence
from typing import cast as typing_cast

from ag_ui.core import (
    AssistantMessage,
    BinaryInputContent,
    FunctionCall,
    TextInputContent,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
    DocumentUrl,
    FilePart,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
    VideoUrl,
)

AgUiMessagePayload = dict[str, object]


def serialize_thread_transcript(messages: Sequence[ModelMessage]) -> list[AgUiMessagePayload]:
    """Convert canonical PydanticAI messages into AG-UI message payloads."""

    message_index = 0
    transcript: list[AgUiMessagePayload] = []

    def next_message_id(prefix: str) -> str:
        nonlocal message_index
        message_index += 1
        return f"{prefix}-{message_index}"

    for message in messages:
        if isinstance(message, ModelRequest):
            transcript.extend(_serialize_request_message(message, next_message_id=next_message_id))
            continue
        transcript.extend(_serialize_response_message(message, next_message_id=next_message_id))

    return transcript


def _serialize_request_message(
    message: ModelRequest,
    *,
    next_message_id: Callable[[str], str],
) -> list[AgUiMessagePayload]:
    payloads: list[AgUiMessagePayload] = []
    for part in message.parts:
        if isinstance(part, SystemPromptPart):
            continue
        if isinstance(part, UserPromptPart):
            payloads.append(
                _dump_message(
                    UserMessage(
                        id=next_message_id("user"),
                        content=_serialize_user_content(part.content),
                    )
                )
            )
            continue
        if isinstance(part, ToolReturnPart):
            payloads.append(
                _dump_message(
                    ToolMessage(
                        id=next_message_id("tool"),
                        tool_call_id=part.tool_call_id,
                        content=_serialize_tool_return_content(part.content),
                    )
                )
            )
            continue
        if isinstance(part, RetryPromptPart):
            payloads.append(
                _dump_message(
                    UserMessage(
                        id=next_message_id("retry"),
                        content=_serialize_retry_prompt_content(part.content),
                    )
                )
            )
    return payloads


def _serialize_response_message(
    message: ModelResponse,
    *,
    next_message_id: Callable[[str], str],
) -> list[AgUiMessagePayload]:
    assistant_text_parts: list[str] = []
    assistant_tool_calls: list[ToolCall] = []
    followup_messages: list[AgUiMessagePayload] = []

    for part in message.parts:
        if isinstance(part, TextPart):
            assistant_text_parts.append(part.content)
            continue
        if isinstance(part, FilePart):
            assistant_text_parts.append(_file_part_label(part))
            continue
        if isinstance(part, (ToolCallPart, BuiltinToolCallPart)):
            assistant_tool_calls.append(
                ToolCall(
                    id=part.tool_call_id,
                    function=FunctionCall(
                        name=part.tool_name,
                        arguments=part.args_as_json_str(),
                    ),
                )
            )
            continue
        if isinstance(part, BuiltinToolReturnPart):
            followup_messages.append(
                _dump_message(
                    ToolMessage(
                        id=next_message_id("tool"),
                        tool_call_id=part.tool_call_id,
                        content=_serialize_tool_return_content(part.content),
                    )
                )
            )
            continue
        if isinstance(part, ThinkingPart):
            continue

    payloads: list[AgUiMessagePayload] = []
    if assistant_text_parts or assistant_tool_calls:
        payloads.append(
            _dump_message(
                AssistantMessage(
                    id=next_message_id("assistant"),
                    content="".join(assistant_text_parts) or None,
                    toolCalls=assistant_tool_calls or None,
                )
            )
        )
    payloads.extend(followup_messages)
    return payloads


def _serialize_user_content(content: object) -> str | list[TextInputContent | BinaryInputContent]:
    if isinstance(content, str):
        return content
    if not isinstance(content, Sequence):
        return str(content)

    ag_ui_parts: list[TextInputContent | BinaryInputContent] = []
    for item in content:
        if isinstance(item, str):
            ag_ui_parts.append(TextInputContent(text=item))
            continue
        if isinstance(item, BinaryContent):
            ag_ui_parts.append(
                BinaryInputContent(
                    id=item.identifier,
                    mime_type=item.media_type,
                    data=b64encode(item.data).decode("ascii"),
                )
            )
            continue
        if isinstance(item, (ImageUrl, AudioUrl, VideoUrl, DocumentUrl)):
            ag_ui_parts.append(
                BinaryInputContent(
                    id=item.identifier,
                    mime_type=item.media_type or "application/octet-stream",
                    url=item.url,
                )
            )
    if len(ag_ui_parts) == 1 and isinstance(ag_ui_parts[0], TextInputContent):
        return ag_ui_parts[0].text
    return ag_ui_parts


def _serialize_retry_prompt_content(content: object) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str, sort_keys=True)


def _serialize_tool_return_content(content: object) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str, sort_keys=True)


def _file_part_label(part: FilePart) -> str:
    identifier = part.content.identifier or part.id or "generated-file"
    return f"[Generated file: {identifier} ({part.content.media_type})]"


def _dump_message(
    message: UserMessage | AssistantMessage | ToolMessage,
) -> AgUiMessagePayload:
    return typing_cast(
        "AgUiMessagePayload",
        message.model_dump(mode="json", by_alias=True, exclude_none=True),
    )
