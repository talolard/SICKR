from __future__ import annotations

from ikea_agent.chat.deps import ChatAgentState


def test_chat_agent_state_defaults_are_eval_and_session_ready() -> None:
    state = ChatAgentState()

    assert state.session_id is None
    assert state.branch_from_session_id is None
    assert state.labels == []
    assert state.eval_dataset_name is None
    assert state.eval_case_id is None
    assert state.thread_id is None
    assert state.run_id is None
    assert state.attachments == []


def test_chat_agent_state_accepts_session_and_eval_fields() -> None:
    state = ChatAgentState(
        session_id="session-123",
        branch_from_session_id="session-root",
        labels=["discovery", "layout"],
        eval_dataset_name="local-discovery",
        eval_case_id="case-001",
        thread_id="thread-123",
        run_id="run-123",
    )

    assert state.session_id == "session-123"
    assert state.branch_from_session_id == "session-root"
    assert state.labels == ["discovery", "layout"]
    assert state.eval_dataset_name == "local-discovery"
    assert state.eval_case_id == "case-001"
    assert state.thread_id == "thread-123"
    assert state.run_id == "run-123"
