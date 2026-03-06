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
    assert state.room_3d_snapshots == []


def test_chat_agent_state_accepts_session_and_eval_fields() -> None:
    state = ChatAgentState(
        session_id="session-123",
        branch_from_session_id="session-root",
        labels=["discovery", "layout"],
        eval_dataset_name="local-discovery",
        eval_case_id="case-001",
        thread_id="thread-123",
        run_id="run-123",
        room_3d_snapshots=[
            {
                "snapshot_id": "snap-1",
                "attachment": {
                    "attachment_id": "asset-1",
                    "mime_type": "image/png",
                    "uri": "/attachments/asset-1",
                    "width": None,
                    "height": None,
                },
                "comment": "Need brighter lighting.",
                "captured_at": "2026-03-06T22:00:00Z",
                "camera": {
                    "position_m": [1.0, 1.5, 2.0],
                    "target_m": [1.0, 0.8, 1.0],
                    "fov_deg": 55.0,
                },
                "lighting": {
                    "light_fixture_ids": ["light-1"],
                    "emphasized_light_count": 1,
                },
            }
        ],
    )

    assert state.session_id == "session-123"
    assert state.branch_from_session_id == "session-root"
    assert state.labels == ["discovery", "layout"]
    assert state.eval_dataset_name == "local-discovery"
    assert state.eval_case_id == "case-001"
    assert state.thread_id == "thread-123"
    assert state.run_id == "run-123"
    assert state.room_3d_snapshots[0].snapshot_id == "snap-1"
