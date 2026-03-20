"""Explicit agent index for discovery, metadata, and AG-UI routing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypedDict, cast

from pydantic_ai import Agent

from ikea_agent.chat.agents.floor_plan_intake.agent import (
    AGENT_NAME as FLOOR_PLAN_AGENT_NAME,
)
from ikea_agent.chat.agents.floor_plan_intake.agent import (
    DESCRIPTION as FLOOR_PLAN_DESCRIPTION,
)
from ikea_agent.chat.agents.floor_plan_intake.agent import NOTES as FLOOR_PLAN_NOTES
from ikea_agent.chat.agents.floor_plan_intake.agent import PROMPT as FLOOR_PLAN_PROMPT
from ikea_agent.chat.agents.floor_plan_intake.agent import TOOL_NAMES as FLOOR_PLAN_TOOL_NAMES
from ikea_agent.chat.agents.floor_plan_intake.agent import build_floor_plan_intake_agent
from ikea_agent.chat.agents.floor_plan_intake.deps import FloorPlanIntakeDeps
from ikea_agent.chat.agents.image_analysis.agent import (
    AGENT_NAME as IMAGE_ANALYSIS_AGENT_NAME,
)
from ikea_agent.chat.agents.image_analysis.agent import (
    DESCRIPTION as IMAGE_ANALYSIS_DESCRIPTION,
)
from ikea_agent.chat.agents.image_analysis.agent import NOTES as IMAGE_ANALYSIS_NOTES
from ikea_agent.chat.agents.image_analysis.agent import PROMPT as IMAGE_ANALYSIS_PROMPT
from ikea_agent.chat.agents.image_analysis.agent import TOOL_NAMES as IMAGE_ANALYSIS_TOOL_NAMES
from ikea_agent.chat.agents.image_analysis.agent import build_image_analysis_agent
from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.search.agent import AGENT_NAME as SEARCH_AGENT_NAME
from ikea_agent.chat.agents.search.agent import DESCRIPTION as SEARCH_DESCRIPTION
from ikea_agent.chat.agents.search.agent import NOTES as SEARCH_NOTES
from ikea_agent.chat.agents.search.agent import PROMPT as SEARCH_PROMPT
from ikea_agent.chat.agents.search.agent import TOOL_NAMES as SEARCH_TOOL_NAMES
from ikea_agent.chat.agents.search.agent import build_search_agent
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.state import (
    FloorPlanIntakeAgentState,
    ImageAnalysisAgentState,
    SearchAgentState,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore

AnyAgentDeps = FloorPlanIntakeDeps | SearchAgentDeps | ImageAnalysisAgentDeps


@dataclass(frozen=True, slots=True)
class _AgentRegistration:
    """Single source of truth for one registered agent."""

    name: str
    description: str
    notes: str
    prompt_markdown_loader: Callable[[], str]
    tool_names: tuple[str, ...]
    build_agent: Callable[[str | None], Agent[object, str]]
    build_deps: Callable[[ChatRuntime, AttachmentStore], AnyAgentDeps]


class AgentCatalogItem(TypedDict):
    """Agent fields used by frontend navigation and runtime routing."""

    name: str
    description: str
    agent_key: str
    ag_ui_path: str
    web_path: str


class AgentDescription(AgentCatalogItem):
    """Full agent metadata payload returned by backend endpoints."""

    prompt_markdown: str
    tools: list[str]
    notes: str


def _agent_key(name: str) -> str:
    return f"agent_{name}"


def _ag_ui_path(name: str) -> str:
    return f"/ag-ui/agents/{name}"


def _web_path(name: str) -> str:
    return f"/agents/{name}/chat/"


def _agent_item(*, name: str, description: str) -> AgentCatalogItem:
    return AgentCatalogItem(
        name=name,
        description=description,
        agent_key=_agent_key(name),
        ag_ui_path=_ag_ui_path(name),
        web_path=_web_path(name),
    )


_REGISTERED_AGENTS: tuple[_AgentRegistration, ...] = (
    _AgentRegistration(
        name=FLOOR_PLAN_AGENT_NAME,
        description=FLOOR_PLAN_DESCRIPTION,
        notes=FLOOR_PLAN_NOTES,
        prompt_markdown_loader=FLOOR_PLAN_PROMPT.read_markdown,
        tool_names=tuple(FLOOR_PLAN_TOOL_NAMES),
        build_agent=lambda explicit_model: cast(
            "Agent[object, str]",
            build_floor_plan_intake_agent(explicit_model=explicit_model),
        ),
        build_deps=lambda runtime, attachment_store: FloorPlanIntakeDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            floor_plan_scene_store=FloorPlanSceneStore(),
            state=FloorPlanIntakeAgentState(),
        ),
    ),
    _AgentRegistration(
        name=SEARCH_AGENT_NAME,
        description=SEARCH_DESCRIPTION,
        notes=SEARCH_NOTES,
        prompt_markdown_loader=SEARCH_PROMPT.read_markdown,
        tool_names=tuple(SEARCH_TOOL_NAMES),
        build_agent=lambda explicit_model: cast(
            "Agent[object, str]",
            build_search_agent(explicit_model=explicit_model),
        ),
        build_deps=lambda runtime, attachment_store: SearchAgentDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            state=SearchAgentState(),
        ),
    ),
    _AgentRegistration(
        name=IMAGE_ANALYSIS_AGENT_NAME,
        description=IMAGE_ANALYSIS_DESCRIPTION,
        notes=IMAGE_ANALYSIS_NOTES,
        prompt_markdown_loader=IMAGE_ANALYSIS_PROMPT.read_markdown,
        tool_names=tuple(IMAGE_ANALYSIS_TOOL_NAMES),
        build_agent=lambda explicit_model: cast(
            "Agent[object, str]",
            build_image_analysis_agent(explicit_model=explicit_model),
        ),
        build_deps=lambda runtime, attachment_store: ImageAnalysisAgentDeps(
            runtime=runtime,
            attachment_store=attachment_store,
            state=ImageAnalysisAgentState(),
        ),
    ),
)

AGENTS: tuple[AgentCatalogItem, ...] = tuple(
    _agent_item(name=entry.name, description=entry.description) for entry in _REGISTERED_AGENTS
)


def _index_by_name() -> dict[str, AgentCatalogItem]:
    return {item["name"]: item for item in AGENTS}


def _registration_by_name(name: str) -> _AgentRegistration:
    for entry in _REGISTERED_AGENTS:
        if entry.name == name:
            return entry
    _ = get_agent(name)
    msg = f"No registration configured for agent `{name}`."
    raise KeyError(msg)


def get_agent(name: str) -> AgentCatalogItem:
    """Return one registered agent metadata item by name."""

    item = _index_by_name().get(name)
    if item is None:
        available = ", ".join(sorted(_index_by_name()))
        msg = f"Unknown agent `{name}`. Available: {available}."
        raise KeyError(msg)
    return item


def list_agent_catalog() -> list[AgentCatalogItem]:
    """Return all registered agents with stable routing metadata."""

    return list(AGENTS)


def describe_agent(name: str) -> AgentDescription:
    """Return full metadata for one agent."""

    item = get_agent(name)
    registration = _registration_by_name(name)
    return AgentDescription(
        name=item["name"],
        description=item["description"],
        agent_key=item["agent_key"],
        ag_ui_path=item["ag_ui_path"],
        web_path=item["web_path"],
        prompt_markdown=registration.prompt_markdown_loader(),
        tools=list(registration.tool_names),
        notes=registration.notes,
    )


def build_agent_ag_ui_agent(
    name: str,
    *,
    explicit_model: str | None = None,
) -> Agent[object, str]:
    """Build one AG-UI agent instance for a registered agent."""

    return _registration_by_name(name).build_agent(explicit_model)


def build_agent_deps(
    name: str,
    *,
    runtime: ChatRuntime,
    attachment_store: AttachmentStore,
) -> AnyAgentDeps:
    """Build typed dependencies for one registered agent."""

    return _registration_by_name(name).build_deps(runtime, attachment_store)


def clone_agent_deps_for_request(base_deps: AnyAgentDeps) -> AnyAgentDeps:
    """Return one per-request deps container with fresh mutable state."""

    if isinstance(base_deps, FloorPlanIntakeDeps):
        return FloorPlanIntakeDeps(
            runtime=base_deps.runtime,
            attachment_store=base_deps.attachment_store,
            floor_plan_scene_store=base_deps.floor_plan_scene_store,
            state=FloorPlanIntakeAgentState(),
        )
    if isinstance(base_deps, SearchAgentDeps):
        return SearchAgentDeps(
            runtime=base_deps.runtime,
            attachment_store=base_deps.attachment_store,
            state=SearchAgentState(),
        )
    if isinstance(base_deps, ImageAnalysisAgentDeps):
        return ImageAnalysisAgentDeps(
            runtime=base_deps.runtime,
            attachment_store=base_deps.attachment_store,
            state=ImageAnalysisAgentState(),
        )
    msg = f"Unsupported deps type `{type(base_deps)!r}`."
    raise TypeError(msg)


__all__ = [
    "AGENTS",
    "AgentCatalogItem",
    "AgentDescription",
    "AnyAgentDeps",
    "build_agent_ag_ui_agent",
    "build_agent_deps",
    "clone_agent_deps_for_request",
    "describe_agent",
    "get_agent",
    "list_agent_catalog",
]
