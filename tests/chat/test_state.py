from __future__ import annotations

from ikea_agent.chat.agents.state import CommonAgentState, SearchAgentState
from ikea_agent.shared.types import (
    SearchBatchToolResult,
    SearchQueryToolResult,
    ShortRetrievalResult,
)


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


def test_search_agent_state_parses_bundle_proposals_into_typed_models() -> None:
    state = SearchAgentState(
        thread_id="thread-123",
        bundle_proposals=[
            {
                "bundle_id": "bundle-1",
                "title": "Desk starter",
                "notes": "Good first pass.",
                "budget_cap_eur": 200.0,
                "items": [
                    {
                        "item_id": "chair-1",
                        "product_name": "Chair One",
                        "description_text": "Desk chair",
                        "price_eur": 79.99,
                        "quantity": 1,
                        "line_total_eur": 79.99,
                        "reason": "Primary desk chair",
                    }
                ],
                "bundle_total_eur": 79.99,
                "validations": [
                    {
                        "kind": "pricing_complete",
                        "status": "pass",
                        "message": "All bundle items have prices, so the total is complete.",
                    }
                ],
                "created_at": "2026-03-11T11:00:00+00:00",
                "run_id": "run-1",
            }
        ],
    )

    assert state.bundle_proposals[0].bundle_id == "bundle-1"
    assert state.bundle_proposals[0].items[0].product_name == "Chair One"
    assert state.bundle_proposals[0].validations[0].kind == "pricing_complete"


def test_search_agent_state_parses_grounded_products_into_typed_models() -> None:
    state = SearchAgentState(
        thread_id="thread-123",
        grounded_products=[
            {
                "product_id": "chair-1",
                "product_name": "Chair One",
                "query_id": "desk",
                "semantic_query": "small desk chair",
            }
        ],
    )

    assert state.grounded_products[0].product_id == "chair-1"
    assert state.grounded_products[0].query_id == "desk"


def test_search_agent_state_remembers_grounded_products_without_duplicates() -> None:
    state = SearchAgentState(thread_id="thread-123")

    state.remember_search_batch(
        SearchBatchToolResult(
            queries=[
                SearchQueryToolResult(
                    query_id="lighting",
                    semantic_query="portable lamp",
                    results=[
                        ShortRetrievalResult(
                            product_id="lamp-1",
                            product_name="Lamp One",
                            product_type="Lighting",
                            description_text="Portable lamp",
                            main_category="lighting",
                            sub_category="portable_lamp",
                            width_cm=None,
                            depth_cm=None,
                            height_cm=None,
                            price_eur=19.99,
                        )
                    ],
                    total_candidates=1,
                    returned_count=1,
                ),
                SearchQueryToolResult(
                    query_id="shelf",
                    semantic_query="floating shelf",
                    results=[
                        ShortRetrievalResult(
                            product_id="lamp-1",
                            product_name="Lamp One",
                            product_type="Lighting",
                            description_text="Portable lamp",
                            main_category="lighting",
                            sub_category="portable_lamp",
                            width_cm=None,
                            depth_cm=None,
                            height_cm=None,
                            price_eur=19.99,
                        ),
                        ShortRetrievalResult(
                            product_id="shelf-1",
                            product_name="Shelf One",
                            product_type="Storage",
                            description_text="Floating shelf",
                            main_category="storage",
                            sub_category="wall_shelf",
                            width_cm=None,
                            depth_cm=None,
                            height_cm=None,
                            price_eur=24.99,
                        ),
                    ],
                    total_candidates=2,
                    returned_count=2,
                ),
            ]
        )
    )

    assert [item.product_id for item in state.grounded_products] == ["lamp-1", "shelf-1"]
    assert state.grounded_product_ids() == {"lamp-1", "shelf-1"}
