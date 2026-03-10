"""Subagent entrypoints for chat subagents."""

from ikea_agent.chat.subagents.index import (
    SUBAGENTS,
    build_subagent_ag_ui_agent,
    describe_subagent,
    get_subagent,
    get_subgraph_agent,
    list_subagent_catalog,
)

__all__ = [
    "SUBAGENTS",
    "build_subagent_ag_ui_agent",
    "describe_subagent",
    "get_subagent",
    "get_subgraph_agent",
    "list_subagent_catalog",
]
