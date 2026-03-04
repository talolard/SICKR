from __future__ import annotations

from pathlib import Path

import duckdb

from tal_maria_ikea.phase3.repository import (
    ConversationMessageEvent,
    ConversationThreadEvent,
    ItemRatingEvent,
    Phase3Repository,
    PromptRunEvent,
    PromptTurnEvent,
    ResultDiffRow,
    SearchRequestEvent,
    SearchResultSnapshotRow,
    TurnRatingEvent,
)


def _setup_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))
    connection.execute(Path("sql/42_phase3_runtime.sql").read_text(encoding="utf-8"))


def test_insert_search_request_and_expansion_event() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    repository = Phase3Repository(connection)

    repository.insert_search_request(
        SearchRequestEvent(
            request_id="req-1",
            query_text="couch 100cm under 100 eur",
            user_ref="user-1",
            session_ref="session-1",
            expansion_mode="auto",
            expansion_applied=True,
            filter_timing_mode="embed_then_filter",
            rerank_enabled=True,
            request_source="web",
            latency_ms=123,
        )
    )
    repository.insert_expansion_event(
        expansion_event_id="exp-1",
        request_id="req-1",
        prompt_template_key="expand-default",
        prompt_template_version="v1",
        expanded_query_text="sofa width <= 100cm price <= 100",
        extracted_filters={"max_price_eur": 100.0, "width_max_cm": 100.0},
        confidence=0.9,
        heuristic_reason="constraint_query_detected",
        applied=True,
    )

    row = connection.execute(
        """
        SELECT query_text, expansion_mode, rerank_enabled
        FROM app.search_request_v2
        WHERE request_id = 'req-1'
        """
    ).fetchone()
    assert row == ("couch 100cm under 100 eur", "auto", True)

    expansion_row = connection.execute(
        """
        SELECT extracted_filters_json, applied
        FROM app.search_expansion_event
        WHERE expansion_event_id = 'exp-1'
        """
    ).fetchone()
    assert expansion_row is not None
    assert "max_price_eur" in str(expansion_row[0])
    assert expansion_row[1] is True


def test_result_snapshots_and_diff_view() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    repository = Phase3Repository(connection)
    connection.execute(
        """
        INSERT INTO app.products_canonical (
            canonical_product_key,
            product_id,
            unique_id,
            country,
            product_name,
            product_type,
            description_text
        ) VALUES ('1-DE', 1, 'uid-1', 'Germany', 'Lamp', 'Floor lamp', 'Warm light')
        """
    )

    repository.insert_result_snapshots(
        [
            SearchResultSnapshotRow(
                snapshot_id="snap-1",
                request_id="req-2",
                ranking_stage="semantic_before_rerank",
                rank_position=1,
                canonical_product_key="1-DE",
                semantic_score=0.88,
                rerank_score=None,
                score_explanation="semantic",
            ),
            SearchResultSnapshotRow(
                snapshot_id="snap-2",
                request_id="req-2",
                ranking_stage="after_rerank",
                rank_position=2,
                canonical_product_key="1-DE",
                semantic_score=0.88,
                rerank_score=0.42,
                score_explanation="reranked",
            ),
        ]
    )

    diff_rows = repository.list_result_diff("req-2")
    assert diff_rows == (
        ResultDiffRow(
            canonical_product_key="1-DE",
            product_name="Lamp",
            description_text="Warm light",
            rank_before=1,
            rank_after=2,
            semantic_score=0.88,
            rerank_score=0.42,
            rank_delta=-1,
        ),
    )
    assert repository.list_result_keys_for_request("req-2", limit=5) == ("1-DE",)
    hydrated_results = repository.list_results_for_request("req-2")
    assert hydrated_results[0].canonical_product_key == "1-DE"
    assert hydrated_results[0].product_name == "Lamp"

    repository.upsert_query_cache(
        query_signature_hash="qsig-1",
        request_id="req-2",
        query_text="lamp",
        filters_json='{"sort":"relevance"}',
        cache_config_hash="cfg-1",
        ttl_hours=24,
    )
    query_cache_row = repository.get_query_cache(
        query_signature_hash="qsig-1",
        cache_config_hash="cfg-1",
    )
    assert query_cache_row is not None
    assert query_cache_row.request_id == "req-2"

    repository.upsert_summary_cache(
        summary_cache_key="sum-1",
        request_id="req-2",
        query_signature_hash="qsig-1",
        resultset_hash="rset-1",
        summary_config_hash="scfg-1",
        summary_json='{"summary":"ok","items":[]}',
        ttl_hours=24,
    )
    summary_cache_row = repository.get_summary_cache(
        summary_cache_key="sum-1",
        summary_config_hash="scfg-1",
    )
    assert summary_cache_row is not None
    assert summary_cache_row.summary_json == '{"summary":"ok","items":[]}'


def test_prompt_conversation_and_ratings_roundtrip() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    repository = Phase3Repository(connection)

    repository.insert_prompt_run(
        PromptRunEvent(
            prompt_run_id="run-1",
            request_id="req-3",
            variant_key="summary-default",
            variant_version="v1",
            rendered_system_prompt="You are a helper.",
            rendered_prompt_hash="hash-1",
            user_prompt="Need hallway lamps",
            context_payload_hash="ctx-hash",
            model_name="gemini-2.5-flash",
            status="ok",
            latency_ms=210,
            error_message=None,
            generation_config_json='{"system_instruction":"You are a helper."}',
        )
    )
    repository.upsert_conversation_thread(
        ConversationThreadEvent(
            conversation_id="conv-1",
            request_id="req-3",
            user_ref="user-1",
            session_ref="session-1",
            title="Hallway lighting",
            is_active=True,
        )
    )
    repository.insert_prompt_turn(
        PromptTurnEvent(
            turn_id="turn-1",
            prompt_run_id="run-1",
            conversation_id="conv-1",
            summary_text="Use layered warm lighting.",
            response_json={"summary": "Use layered warm lighting.", "items": ["1-DE"]},
        )
    )
    repository.insert_conversation_message(
        ConversationMessageEvent(
            message_id="msg-1",
            conversation_id="conv-1",
            role="user",
            content_text="Why this lamp?",
            prompt_run_id=None,
        )
    )
    repository.insert_turn_rating(
        TurnRatingEvent(
            turn_rating_id="turn-rating-1",
            turn_id="turn-1",
            request_id="req-3",
            prompt_run_id="run-1",
            thumb="up",
            reason_tags=("helpful", "clear"),
            note="good summary",
            user_ref="user-1",
            session_ref="session-1",
        )
    )
    repository.insert_item_rating(
        ItemRatingEvent(
            item_rating_id="item-rating-1",
            turn_id="turn-1",
            request_id="req-3",
            prompt_run_id="run-1",
            canonical_product_key="1-DE",
            thumb="down",
            reason_tags=("too_expensive",),
            note=None,
            user_ref="user-1",
            session_ref="session-1",
        )
    )

    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM app.prompt_run),
            (SELECT generation_config_json FROM app.prompt_run WHERE prompt_run_id = 'run-1'),
            (SELECT COUNT(*) FROM app.prompt_response_turn),
            (SELECT COUNT(*) FROM app.conversation_message),
            (SELECT COUNT(*) FROM app.feedback_turn_rating),
            (SELECT COUNT(*) FROM app.feedback_item_rating)
        """
    ).fetchone()
    assert counts == (1, '{"system_instruction":"You are a helper."}', 1, 1, 1, 1)
    threads = repository.list_conversation_threads(limit=10)
    assert len(threads) == 1
    messages = repository.list_conversation_messages(conversation_id="conv-1", limit=10)
    assert len(messages) == 1
    assert repository.latest_turn_id_for_prompt_run("run-1") == "turn-1"
    assert repository.summarize_turn_feedback() == (("up", 1),)
    assert repository.summarize_item_feedback() == (("down", 1),)
