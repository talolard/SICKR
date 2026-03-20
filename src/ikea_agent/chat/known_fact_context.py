"""Render durable room and project facts into agent context."""

from __future__ import annotations

from ikea_agent.shared.types import KnownFactKind, KnownFactMemory, RoomType

_KIND_PRIORITY: dict[KnownFactKind, int] = {
    "constraint": 0,
    "fact": 1,
    "preference": 2,
}


def format_known_fact_context(
    *,
    room_title: str | None,
    room_type: RoomType | None,
    room_facts: list[KnownFactMemory],
    project_facts: list[KnownFactMemory],
) -> str | None:
    """Render stored room/project facts into dynamic agent instructions."""

    profile_lines = _room_profile_lines(room_title=room_title, room_type=room_type)
    room_fact_lines = _fact_lines(label="Room facts", facts=room_facts)
    project_fact_lines = _fact_lines(label="Project facts", facts=project_facts)
    sections = [
        section for section in (profile_lines, room_fact_lines, project_fact_lines) if section
    ]
    if not sections:
        return None
    return "\n\n".join(sections)


def _room_profile_lines(*, room_title: str | None, room_type: RoomType | None) -> str | None:
    lines: list[str] = []
    if room_title:
        lines.append(f"- room title: {room_title}")
    if room_type:
        lines.append(f"- room type: {room_type}")
    if not lines:
        return None
    return "\n".join(["Current room profile:", *lines])


def _fact_lines(*, label: str, facts: list[KnownFactMemory]) -> str | None:
    if not facts:
        return None
    ordered = [
        fact
        for _, fact in sorted(
            enumerate(facts),
            key=lambda item: (_KIND_PRIORITY[item[1].kind], item[0]),
        )
    ]
    return "\n".join([f"{label}:", *[f"- {fact.kind}: {fact.summary}" for fact in ordered]])
