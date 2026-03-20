from __future__ import annotations

from ikea_agent.chat.agents.shared import _fact_instruction_text
from ikea_agent.chat.agents.state import CommonAgentState
from ikea_agent.chat.known_fact_context import format_known_fact_context
from ikea_agent.shared.types import KnownFactMemory
from ikea_agent.tools.facts import FactNoteInput, note_to_known_fact_input


def test_note_to_known_fact_input_normalizes_agent_authored_summary() -> None:
    fact_input = note_to_known_fact_input(
        FactNoteInput(
            key="User Has Toddlers",
            kind="constraint",
            summary="User has toddlers, keep things elevated.",
            source="They said low tables feel risky around the toddler.",
        )
    )

    assert fact_input.signal_key == "agent_note"
    assert fact_input.value == "user_has_toddlers"
    assert fact_input.summary == "User has toddlers, keep things elevated."
    assert fact_input.source_message_text == "They said low tables feel risky around the toddler."


def test_format_known_fact_context_renders_room_and_project_blocks() -> None:
    instruction = format_known_fact_context(
        room_title="Living room",
        room_type="living_room",
        room_facts=[
            KnownFactMemory(
                fact_id="rfact-1",
                scope="room",
                signal_key="agent_note",
                kind="constraint",
                value="user_has_toddlers",
                summary="User has toddlers, keep things elevated.",
                source_message_text="A low table sounds risky.",
                created_at="2026-03-17T11:00:00+00:00",
                updated_at="2026-03-17T11:05:00+00:00",
                run_id="run-2",
            )
        ],
        project_facts=[
            KnownFactMemory(
                fact_id="pfact-1",
                scope="project",
                signal_key="agent_note",
                kind="fact",
                value="avoid_drilling",
                summary="User cannot drill into the walls.",
                source_message_text="We cannot drill into the walls.",
                created_at="2026-03-17T10:00:00+00:00",
                updated_at="2026-03-17T10:05:00+00:00",
                run_id="run-1",
            )
        ],
    )

    assert instruction is not None
    assert "Current room profile:" in instruction
    assert "room title: Living room" in instruction
    assert "room type: living_room" in instruction
    assert "Room facts:" in instruction
    assert "Project facts:" in instruction
    assert "- constraint: User has toddlers, keep things elevated." in instruction
    assert "- fact: User cannot drill into the walls." in instruction


def test_fact_instruction_text_distinguishes_durable_facts_from_search_intent() -> None:
    instruction = _fact_instruction_text(CommonAgentState())

    assert "remember_room_fact" in instruction
    assert "remember_project_fact" in instruction
    assert "rename_room" in instruction
    assert "set_room_type" in instruction
    assert "Looking for a couch, table, or lamp is part of the current request" in instruction
