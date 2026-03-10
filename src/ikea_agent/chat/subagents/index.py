"""Explicit subagent index for discovery, metadata, and AG-UI routing."""

from __future__ import annotations

from pydantic_ai import Agent

from ikea_agent.chat.subagents.base import (
    SubagentCatalogItem,
    SubagentDescription,
    SubgraphAgent,
)
from ikea_agent.chat.subagents.floor_plan_intake.agent import FloorPlannerSubgraphAgent

SUBGRAPH_AGENTS: tuple[type[SubgraphAgent], ...] = (FloorPlannerSubgraphAgent,)


def _index_by_name() -> dict[str, type[SubgraphAgent]]:
    return {subgraph_cls.subagent_name: subgraph_cls for subgraph_cls in SUBGRAPH_AGENTS}


def get_subgraph_agent(name: str) -> type[SubgraphAgent]:
    """Return one registered subgraph-agent class by name."""

    item = _index_by_name().get(name)
    if item is None:
        available = ", ".join(sorted(_index_by_name()))
        msg = f"Unknown subagent `{name}`. Available: {available}."
        raise KeyError(msg)
    return item


def list_subagent_catalog() -> list[SubagentCatalogItem]:
    """Return all registered subagents with stable routing metadata."""

    return [subgraph_cls.build_catalog_item() for subgraph_cls in SUBGRAPH_AGENTS]


def describe_subagent(name: str) -> SubagentDescription:
    """Return full metadata for one subagent."""

    return get_subgraph_agent(name).build_metadata()


def build_subagent_ag_ui_agent(
    name: str,
    *,
    explicit_model: str | None = None,
) -> Agent[None, str]:
    """Build one AG-UI agent instance for a registered subgraph-agent class."""

    return get_subgraph_agent(name).build_agent(explicit_model=explicit_model)


__all__ = [
    "SUBGRAPH_AGENTS",
    "SubagentCatalogItem",
    "SubagentDescription",
    "build_subagent_ag_ui_agent",
    "describe_subagent",
    "get_subgraph_agent",
    "list_subagent_catalog",
]
