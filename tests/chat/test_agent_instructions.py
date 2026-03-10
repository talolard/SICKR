from ikea_agent.chat.agents.search.agent import PROMPT


def test_agent_instructions_require_explicit_zero_result_grounding() -> None:
    instructions = PROMPT.instruction_text()

    assert "If `returned_count` is 0" in instructions
    assert "no matches were found" in instructions
    assert "broaden constraints" in instructions
