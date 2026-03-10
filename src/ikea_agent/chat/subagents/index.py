"""Explicit subagent index for discovery, metadata, and AG-UI routing."""

from __future__ import annotations

from typing import TypedDict

from pydantic_ai import Agent

from ikea_agent.chat.deps import ChatAgentDeps
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    DESCRIPTION as FLOOR_PLAN_DESCRIPTION,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    NOTES as FLOOR_PLAN_NOTES,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    PROMPT as FLOOR_PLAN_PROMPT,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    SUBAGENT_NAME as FLOOR_PLAN_SUBAGENT_NAME,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    TOOL_NAMES as FLOOR_PLAN_TOOL_NAMES,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import (
    build_floor_plan_intake_agent,
)


class SubagentCatalogItem(TypedDict):
    """Subagent fields used by frontend navigation and runtime routing."""

    name: str
    description: str
    agent_key: str
    ag_ui_path: str
    web_path: str


class SubagentDescription(SubagentCatalogItem):
    """Full subagent metadata payload returned by backend endpoints."""

    prompt_markdown: str
    tools: list[str]
    notes: str


def _agent_key(name: str) -> str:
    return f"subagent_{name}"


def _ag_ui_path(name: str) -> str:
    return f"/ag-ui/subagents/{name}"


def _web_path(name: str) -> str:
    return f"/subagents/{name}/chat/"


def _floor_plan_catalog_item() -> SubagentCatalogItem:
    return SubagentCatalogItem(
        name=FLOOR_PLAN_SUBAGENT_NAME,
        description=FLOOR_PLAN_DESCRIPTION,
        agent_key=_agent_key(FLOOR_PLAN_SUBAGENT_NAME),
        ag_ui_path=_ag_ui_path(FLOOR_PLAN_SUBAGENT_NAME),
        web_path=_web_path(FLOOR_PLAN_SUBAGENT_NAME),
    )


SUBAGENTS: tuple[SubagentCatalogItem, ...] = (_floor_plan_catalog_item(),)


def _index_by_name() -> dict[str, SubagentCatalogItem]:
    return {item["name"]: item for item in SUBAGENTS}


def get_subagent(name: str) -> SubagentCatalogItem:
    """Return one registered subagent metadata item by name."""

    item = _index_by_name().get(name)
    if item is None:
        available = ", ".join(sorted(_index_by_name()))
        msg = f"Unknown subagent `{name}`. Available: {available}."
        raise KeyError(msg)
    return item


def get_subgraph_agent(name: str) -> SubagentCatalogItem:
    """Backward-compatible alias for callers still using the old function name."""

    return get_subagent(name)


def list_subagent_catalog() -> list[SubagentCatalogItem]:
    """Return all registered subagents with stable routing metadata."""

    return list(SUBAGENTS)


def describe_subagent(name: str) -> SubagentDescription:
    """Return full metadata for one subagent."""

    item = get_subagent(name)
    if name == FLOOR_PLAN_SUBAGENT_NAME:
        return SubagentDescription(
            name=item["name"],
            description=item["description"],
            agent_key=item["agent_key"],
            ag_ui_path=item["ag_ui_path"],
            web_path=item["web_path"],
            prompt_markdown=FLOOR_PLAN_PROMPT.read_markdown(),
            tools=list(FLOOR_PLAN_TOOL_NAMES),
            notes=FLOOR_PLAN_NOTES,
        )
    msg = f"No metadata builder registered for subagent `{name}`."
    raise KeyError(msg)


def build_subagent_ag_ui_agent(
    name: str,
    *,
    explicit_model: str | None = None,
) -> Agent[ChatAgentDeps, str]:
    """Build one AG-UI agent instance for a registered subagent."""

    if name == FLOOR_PLAN_SUBAGENT_NAME:
        return build_floor_plan_intake_agent(explicit_model=explicit_model)
    _ = get_subagent(name)
    msg = f"No agent builder registered for subagent `{name}`."
    raise KeyError(msg)


__all__ = [
    "SUBAGENTS",
    "SubagentCatalogItem",
    "SubagentDescription",
    "build_subagent_ag_ui_agent",
    "describe_subagent",
    "get_subagent",
    "get_subgraph_agent",
    "list_subagent_catalog",
]
