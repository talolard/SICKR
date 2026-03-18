from __future__ import annotations

from ikea_agent.chat.agents.shared import _preference_instruction_text
from ikea_agent.chat.agents.state import CommonAgentState
from ikea_agent.chat.revealed_preference_memory import format_preference_context
from ikea_agent.shared.types import RevealedPreferenceMemory
from ikea_agent.tools.preferences import PreferenceNoteInput, note_to_memory_input


def test_note_to_memory_input_normalizes_agent_authored_summary() -> None:
    memory_input = note_to_memory_input(
        PreferenceNoteInput(
            key="User Has Toddlers",
            kind="constraint",
            summary="User has toddlers, keep things elevated.",
            source="They said low tables feel risky around the toddler.",
        )
    )

    assert memory_input.signal_key == "agent_note"
    assert memory_input.value == "user_has_toddlers"
    assert memory_input.summary == "User has toddlers, keep things elevated."
    assert memory_input.source_message_text == "They said low tables feel risky around the toddler."


def test_format_preference_context_renders_thread_context_block() -> None:
    instruction = format_preference_context(
        [
            RevealedPreferenceMemory(
                memory_id="rmem-1",
                signal_key="agent_note",
                kind="constraint",
                value="user_has_toddlers",
                summary="User has toddlers, keep things elevated.",
                source_message_text="A low table sounds risky.",
                created_at="2026-03-17T11:00:00+00:00",
                updated_at="2026-03-17T11:05:00+00:00",
                run_id="run-2",
            ),
            RevealedPreferenceMemory(
                memory_id="rmem-2",
                signal_key="agent_note",
                kind="fact",
                value="avoid_drilling",
                summary="User cannot drill into the walls.",
                source_message_text="We cannot drill into the walls.",
                created_at="2026-03-17T10:00:00+00:00",
                updated_at="2026-03-17T10:05:00+00:00",
                run_id="run-1",
            ),
        ]
    )

    assert instruction is not None
    assert "Thread-scoped revealed preferences" in instruction
    assert "- constraint: User has toddlers, keep things elevated." in instruction
    assert "- fact: User cannot drill into the walls." in instruction


def test_preference_instruction_text_distinguishes_durable_facts_from_search_intent() -> None:
    instruction = _preference_instruction_text(CommonAgentState())

    assert "Dogs shed heavily" in instruction
    assert "Dogs bark easily" in instruction
    assert "User loves pink" in instruction
    assert "Looking for a couch, table, or lamp is part of the current search" in instruction
