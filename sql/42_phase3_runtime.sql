-- Phase 3 runtime telemetry, conversation, and feedback tables.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.search_request_v2 (
    request_id VARCHAR PRIMARY KEY,
    query_text VARCHAR NOT NULL,
    user_ref VARCHAR,
    session_ref VARCHAR,
    expansion_mode VARCHAR NOT NULL,
    expansion_applied BOOLEAN NOT NULL DEFAULT false,
    filter_timing_mode VARCHAR NOT NULL,
    rerank_enabled BOOLEAN NOT NULL DEFAULT false,
    request_source VARCHAR,
    latency_ms BIGINT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.search_expansion_event (
    expansion_event_id VARCHAR PRIMARY KEY,
    request_id VARCHAR NOT NULL,
    prompt_template_key VARCHAR,
    prompt_template_version VARCHAR,
    expanded_query_text VARCHAR,
    extracted_filters_json VARCHAR,
    confidence DOUBLE,
    heuristic_reason VARCHAR,
    applied BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.search_result_snapshot (
    snapshot_id VARCHAR PRIMARY KEY,
    request_id VARCHAR NOT NULL,
    ranking_stage VARCHAR NOT NULL,
    rank_position INTEGER NOT NULL,
    canonical_product_key VARCHAR NOT NULL,
    semantic_score DOUBLE,
    rerank_score DOUBLE,
    score_explanation VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.prompt_run (
    prompt_run_id VARCHAR PRIMARY KEY,
    request_id VARCHAR NOT NULL,
    variant_key VARCHAR NOT NULL,
    variant_version VARCHAR NOT NULL,
    rendered_system_prompt VARCHAR NOT NULL,
    rendered_prompt_hash VARCHAR NOT NULL,
    user_prompt VARCHAR NOT NULL,
    context_payload_hash VARCHAR,
    model_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    latency_ms BIGINT,
    error_message VARCHAR,
    generation_config_json VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

ALTER TABLE app.prompt_run ADD COLUMN IF NOT EXISTS generation_config_json VARCHAR;

CREATE TABLE IF NOT EXISTS app.prompt_response_turn (
    turn_id VARCHAR PRIMARY KEY,
    prompt_run_id VARCHAR NOT NULL,
    conversation_id VARCHAR NOT NULL,
    summary_text VARCHAR,
    response_json VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.conversation_thread (
    conversation_id VARCHAR PRIMARY KEY,
    request_id VARCHAR NOT NULL,
    user_ref VARCHAR,
    session_ref VARCHAR,
    title VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.conversation_message (
    message_id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content_text VARCHAR NOT NULL,
    prompt_run_id VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.feedback_turn_rating (
    turn_rating_id VARCHAR PRIMARY KEY,
    turn_id VARCHAR NOT NULL,
    request_id VARCHAR NOT NULL,
    prompt_run_id VARCHAR NOT NULL,
    thumb VARCHAR NOT NULL,
    reason_tags_json VARCHAR,
    note VARCHAR,
    user_ref VARCHAR,
    session_ref VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.feedback_item_rating (
    item_rating_id VARCHAR PRIMARY KEY,
    turn_id VARCHAR NOT NULL,
    request_id VARCHAR NOT NULL,
    prompt_run_id VARCHAR NOT NULL,
    canonical_product_key VARCHAR NOT NULL,
    thumb VARCHAR NOT NULL,
    reason_tags_json VARCHAR,
    note VARCHAR,
    user_ref VARCHAR,
    session_ref VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

CREATE OR REPLACE VIEW app.search_result_diff AS
SELECT
    before_snapshot.request_id,
    before_snapshot.canonical_product_key,
    before_snapshot.rank_position AS rank_before,
    after_snapshot.rank_position AS rank_after,
    before_snapshot.semantic_score,
    after_snapshot.rerank_score,
    (before_snapshot.rank_position - after_snapshot.rank_position) AS rank_delta
FROM app.search_result_snapshot AS before_snapshot
JOIN app.search_result_snapshot AS after_snapshot
  ON before_snapshot.request_id = after_snapshot.request_id
 AND before_snapshot.canonical_product_key = after_snapshot.canonical_product_key
WHERE before_snapshot.ranking_stage = 'semantic_before_rerank'
  AND after_snapshot.ranking_stage = 'after_rerank';
