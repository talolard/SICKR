from ikea_agent.chat.agent import _load_instructions


def test_agent_instructions_require_explicit_zero_result_grounding() -> None:
    instructions = _load_instructions()

    assert "returned_count = 0" in instructions
    assert "no catalog matches were found for that query" in instructions
    assert "do not recommend products for that query" in instructions
