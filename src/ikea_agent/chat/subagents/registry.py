"""Subagent registry used by the shared subagent CLI."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ikea_agent.chat.subagents.floor_plan_intake import run_from_raw_input

SubagentRunner = Callable[[str], Awaitable[dict[str, object]]]


@dataclass(frozen=True, slots=True)
class SubagentRegistration:
    """One subagent registration entry for dispatch and discoverability."""

    name: str
    description: str
    run: SubagentRunner


_REGISTRY: dict[str, SubagentRegistration] = {
    "floor_plan_intake": SubagentRegistration(
        name="floor_plan_intake",
        description="Collect initial room architecture and render iterative floor-plan drafts.",
        run=run_from_raw_input,
    )
}


def get_subagent(name: str) -> SubagentRegistration:
    """Return one registered subagent by name."""

    item = _REGISTRY.get(name)
    if item is None:
        available = ", ".join(sorted(_REGISTRY))
        msg = f"Unknown subagent `{name}`. Available: {available}."
        raise KeyError(msg)
    return item


def available_subagents() -> list[SubagentRegistration]:
    """Return all known subagent registrations sorted by name."""

    return [entry for _, entry in sorted(_REGISTRY.items(), key=lambda pair: pair[0])]
