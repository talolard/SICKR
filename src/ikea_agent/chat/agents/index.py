"""Explicit agent index for discovery, metadata, and AG-UI routing."""

from __future__ import annotations

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
from ikea_agent.chat.agents.search.agent import AGENT_NAME as SEARCH_AGENT_NAME
from ikea_agent.chat.agents.search.agent import DESCRIPTION as SEARCH_DESCRIPTION
from ikea_agent.chat.agents.search.agent import NOTES as SEARCH_NOTES
from ikea_agent.chat.agents.search.agent import PROMPT as SEARCH_PROMPT
from ikea_agent.chat.agents.search.agent import TOOL_NAMES as SEARCH_TOOL_NAMES
from ikea_agent.chat.agents.search.agent import build_search_agent


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


AGENTS: tuple[AgentCatalogItem, ...] = (
    _agent_item(name=FLOOR_PLAN_AGENT_NAME, description=FLOOR_PLAN_DESCRIPTION),
    _agent_item(name=SEARCH_AGENT_NAME, description=SEARCH_DESCRIPTION),
    _agent_item(name=IMAGE_ANALYSIS_AGENT_NAME, description=IMAGE_ANALYSIS_DESCRIPTION),
)


def _index_by_name() -> dict[str, AgentCatalogItem]:
    return {item["name"]: item for item in AGENTS}


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
    if name == FLOOR_PLAN_AGENT_NAME:
        return AgentDescription(
            name=item["name"],
            description=item["description"],
            agent_key=item["agent_key"],
            ag_ui_path=item["ag_ui_path"],
            web_path=item["web_path"],
            prompt_markdown=FLOOR_PLAN_PROMPT.read_markdown(),
            tools=list(FLOOR_PLAN_TOOL_NAMES),
            notes=FLOOR_PLAN_NOTES,
        )
    if name == SEARCH_AGENT_NAME:
        return AgentDescription(
            name=item["name"],
            description=item["description"],
            agent_key=item["agent_key"],
            ag_ui_path=item["ag_ui_path"],
            web_path=item["web_path"],
            prompt_markdown=SEARCH_PROMPT.read_markdown(),
            tools=list(SEARCH_TOOL_NAMES),
            notes=SEARCH_NOTES,
        )
    if name == IMAGE_ANALYSIS_AGENT_NAME:
        return AgentDescription(
            name=item["name"],
            description=item["description"],
            agent_key=item["agent_key"],
            ag_ui_path=item["ag_ui_path"],
            web_path=item["web_path"],
            prompt_markdown=IMAGE_ANALYSIS_PROMPT.read_markdown(),
            tools=list(IMAGE_ANALYSIS_TOOL_NAMES),
            notes=IMAGE_ANALYSIS_NOTES,
        )
    msg = f"No metadata builder registered for agent `{name}`."
    raise KeyError(msg)


def build_agent_ag_ui_agent(
    name: str,
    *,
    explicit_model: str | None = None,
) -> Agent[object, str]:
    """Build one AG-UI agent instance for a registered agent."""

    if name == FLOOR_PLAN_AGENT_NAME:
        return cast(
            "Agent[object, str]",
            build_floor_plan_intake_agent(explicit_model=explicit_model),
        )
    if name == SEARCH_AGENT_NAME:
        return cast("Agent[object, str]", build_search_agent(explicit_model=explicit_model))
    if name == IMAGE_ANALYSIS_AGENT_NAME:
        return cast(
            "Agent[object, str]",
            build_image_analysis_agent(explicit_model=explicit_model),
        )
    _ = get_agent(name)
    msg = f"No agent builder registered for agent `{name}`."
    raise KeyError(msg)


__all__ = [
    "AGENTS",
    "AgentCatalogItem",
    "AgentDescription",
    "build_agent_ag_ui_agent",
    "describe_agent",
    "get_agent",
    "list_agent_catalog",
]
