"""Dependency container for floor-plan intake agent."""

from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.chat.agents.state import FloorPlanIntakeAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore


@dataclass(slots=True)
class FloorPlanIntakeDeps:
    """Dependencies required by floor-plan intake tools."""

    runtime: ChatRuntime
    attachment_store: AttachmentStore
    floor_plan_scene_store: FloorPlanSceneStore
    state: FloorPlanIntakeAgentState
