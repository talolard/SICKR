"""Shared registry and CLI entrypoints for graph-based chat subagents."""

from ikea_agent.chat.subagents.registry import available_subagents, get_subagent

__all__ = ["available_subagents", "get_subagent"]
