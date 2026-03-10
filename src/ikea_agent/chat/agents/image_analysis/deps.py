"""Dependency container for image-analysis agent."""

from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.chat.agents.state import ImageAnalysisAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore


@dataclass(slots=True)
class ImageAnalysisAgentDeps:
    """Dependencies required by image-analysis tools."""

    runtime: ChatRuntime
    attachment_store: AttachmentStore
    state: ImageAnalysisAgentState
