"""Render durable thread preference memory into agent context.

Revealed preference memory is the small set of durable facts, constraints, and
taste signals that the user exposes during normal conversation and that should
continue to shape later turns on the same thread. The stored records are brief
agent-authored summaries such as "User has toddlers, keep things elevated", not
regex-derived labels for every message. This module is only responsible for
turning the persisted records back into consistent runtime instructions.
"""

from __future__ import annotations

from ikea_agent.shared.types import (
    RevealedPreferenceKind,
    RevealedPreferenceMemory,
)

_KIND_PRIORITY: dict[RevealedPreferenceKind, int] = {
    "constraint": 0,
    "fact": 1,
    "preference": 2,
}


def format_preference_context(
    preferences: list[RevealedPreferenceMemory],
) -> str | None:
    """Render stored thread memory into dynamic agent instructions."""

    if not preferences:
        return None
    ordered = [
        preference
        for _, preference in sorted(
            enumerate(preferences),
            key=lambda item: (_KIND_PRIORITY[item[1].kind], item[0]),
        )
    ]
    lines = [
        "Thread-scoped revealed preferences from prior conversation turns:",
        *[f"- {preference.kind}: {preference.summary}" for preference in ordered],
        "Treat these as active context unless the user explicitly changes them.",
    ]
    return "\n".join(lines)
