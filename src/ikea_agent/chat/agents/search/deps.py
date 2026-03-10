"""Dependency container for search agent."""

from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore


@dataclass(slots=True)
class SearchAgentDeps:
    """Dependencies required by search agent tools."""

    runtime: ChatRuntime
    attachment_store: AttachmentStore
    state: SearchAgentState
