from __future__ import annotations

from ikea_agent.chat.agents.state import CommonAgentState, SearchAgentState


def test_common_agent_state_defaults_are_session_ready() -> None:
    state = CommonAgentState()

    assert state.session_id is None
    assert state.branch_from_session_id is None
    assert state.thread_id is None
    assert state.run_id is None
    assert state.attachments == []


def test_search_agent_state_accepts_room_3d_snapshot_context() -> None:
    state = SearchAgentState(
        session_id="session-123",
        branch_from_session_id="session-root",
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
    assert state.thread_id == "thread-123"
    assert state.run_id == "run-123"
    assert state.room_3d_snapshots[0].snapshot_id == "snap-1"
