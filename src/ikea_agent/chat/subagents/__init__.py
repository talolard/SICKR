"""Class-based subgraph agent entrypoints for chat subagents."""

from ikea_agent.chat.subagents.index import (
    SUBGRAPH_AGENTS,
    build_subagent_ag_ui_agent,
    describe_subagent,
    get_subgraph_agent,
    list_subagent_catalog,
)

__all__ = [
    "SUBGRAPH_AGENTS",
    "build_subagent_ag_ui_agent",
    "describe_subagent",
    "get_subgraph_agent",
    "list_subagent_catalog",
]
