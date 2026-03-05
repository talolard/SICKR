"""Typed dependency container and shared AG-UI state for the chat agent."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import AttachmentRef


class ChatAgentState(BaseModel):
    """State shared between CopilotKit UI and PydanticAI agent runs."""

    attachments: list[AttachmentRef] = Field(default_factory=list)


@dataclass(slots=True)
class ChatAgentDeps:
    """Agent deps that satisfy AG-UI StateHandler via a `state` field."""

    runtime: ChatRuntime
    attachment_store: AttachmentStore
    state: ChatAgentState
