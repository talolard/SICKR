from __future__ import annotations

from ikea_agent.chat.agent import build_room_3d_snapshot_context_payload
from ikea_agent.chat.deps import Room3DSnapshotContext
from ikea_agent.persistence.room_3d_repository import Room3DSnapshotEntry


def test_build_room_3d_snapshot_context_payload_merges_state_and_persisted() -> None:
    state_snapshot = Room3DSnapshotContext.model_validate(
        {
            "snapshot_id": "snap-state-1",
            "attachment": {
                "attachment_id": "asset-state-1",
                "mime_type": "image/png",
                "uri": "/attachments/asset-state-1",
                "width": None,
                "height": None,
            },
            "comment": "Need lamp near desk.",
            "captured_at": "2026-03-06T22:00:00Z",
            "camera": {
                "position_m": [1.1, 1.6, 2.2],
                "target_m": [1.0, 0.9, 1.1],
                "fov_deg": 55.0,
            },
            "lighting": {
                "light_fixture_ids": ["light-1"],
                "emphasized_light_count": 1,
            },
        }
    )
    persisted_snapshot = Room3DSnapshotEntry(
        room_3d_snapshot_id="snap-db-1",
        thread_id="thread-1",
        run_id="run-1",
        snapshot_asset_id="asset-db-1",
        room_3d_asset_id="room3d-asset-1",
        camera={"fov_deg": 60.0},
        lighting={"emphasized_light_count": 2},
        comment="Try brighter wall light.",
        created_at="2026-03-06 22:01:00+00:00",
    )

    payload = build_room_3d_snapshot_context_payload(
        state_snapshots=[state_snapshot],
        persisted_snapshots=[persisted_snapshot],
    )

    assert payload["state_count"] == 1
    assert payload["persisted_count"] == 1
    assert payload["state_snapshots"][0]["snapshot_id"] == "snap-state-1"
    assert payload["persisted_snapshots"][0]["room_3d_snapshot_id"] == "snap-db-1"
