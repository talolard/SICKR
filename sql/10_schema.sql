-- Core schema for Phase 1 semantic search workflow.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.products_raw (
    unique_id VARCHAR,
    product_id BIGINT,
    product_name VARCHAR,
    product_type VARCHAR,
    product_measurements VARCHAR,
    product_description VARCHAR,
    main_category VARCHAR,
    sub_category VARCHAR,
    product_rating VARCHAR,
    product_rating_count VARCHAR,
    badge VARCHAR,
    online_sellable BOOLEAN,
    url VARCHAR,
    price DOUBLE,
    currency VARCHAR,
    discount VARCHAR,
    sale_tag VARCHAR,
    country VARCHAR,
    ingested_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.products_canonical (
    canonical_product_key VARCHAR PRIMARY KEY,
    product_id BIGINT,
    unique_id VARCHAR,
    country VARCHAR NOT NULL,
    product_name VARCHAR NOT NULL,
    product_type VARCHAR,
    description_text VARCHAR,
    main_category VARCHAR,
    sub_category VARCHAR,
    dimensions_text VARCHAR,
    dimensions_type VARCHAR,
    width_cm DOUBLE,
    depth_cm DOUBLE,
    height_cm DOUBLE,
    price_eur DOUBLE,
    currency VARCHAR,
    rating DOUBLE,
    rating_count BIGINT,
    badge VARCHAR,
    online_sellable BOOLEAN,
    url VARCHAR,
    source_updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.product_alias_map (
    canonical_product_key VARCHAR NOT NULL,
    alias_unique_id VARCHAR NOT NULL,
    alias_product_id BIGINT,
    alias_country VARCHAR,
    alias_reason VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (canonical_product_key, alias_unique_id)
);

CREATE TABLE IF NOT EXISTS app.product_family_map (
    family_key VARCHAR NOT NULL,
    canonical_product_key VARCHAR NOT NULL,
    family_reason VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (family_key, canonical_product_key)
);

CREATE TABLE IF NOT EXISTS app.embedding_runs (
    run_id VARCHAR PRIMARY KEY,
    scope VARCHAR NOT NULL,
    strategy_version VARCHAR NOT NULL,
    embedding_model VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    use_batch BOOLEAN NOT NULL,
    subset_limit INTEGER,
    requested_parallelism INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    total_records BIGINT DEFAULT 0,
    embedded_records BIGINT DEFAULT 0,
    failed_records BIGINT DEFAULT 0,
    started_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.product_embeddings (
    canonical_product_key VARCHAR NOT NULL,
    embedding_model VARCHAR NOT NULL,
    strategy_version VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    embedding_vector FLOAT[256],
    embedded_text VARCHAR NOT NULL,
    embedded_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (canonical_product_key, embedding_model, strategy_version)
);

CREATE TABLE IF NOT EXISTS app.query_log (
    query_id VARCHAR PRIMARY KEY,
    query_text VARCHAR NOT NULL,
    result_limit INTEGER NOT NULL,
    category_filter VARCHAR,
    min_price_eur DOUBLE,
    max_price_eur DOUBLE,
    min_width_cm DOUBLE,
    max_width_cm DOUBLE,
    min_depth_cm DOUBLE,
    max_depth_cm DOUBLE,
    min_height_cm DOUBLE,
    max_height_cm DOUBLE,
    exact_width_cm DOUBLE,
    exact_depth_cm DOUBLE,
    exact_height_cm DOUBLE,
    low_confidence BOOLEAN NOT NULL,
    request_source VARCHAR,
    latency_ms BIGINT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.shortlist_global (
    canonical_product_key VARCHAR PRIMARY KEY,
    added_at TIMESTAMP DEFAULT now(),
    note VARCHAR
);

CREATE TABLE IF NOT EXISTS app.eval_prompt_registry (
    prompt_version VARCHAR PRIMARY KEY,
    prompt_text VARCHAR NOT NULL,
    prompt_hash VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.eval_subset_registry (
    subset_id VARCHAR PRIMARY KEY,
    subset_definition VARCHAR NOT NULL,
    subset_hash VARCHAR NOT NULL,
    source_snapshot_ts TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.eval_queries_generated (
    eval_query_id VARCHAR PRIMARY KEY,
    prompt_version VARCHAR NOT NULL,
    subset_id VARCHAR NOT NULL,
    query_text VARCHAR NOT NULL,
    category_hint VARCHAR,
    intent_kind VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.eval_labels (
    eval_query_id VARCHAR NOT NULL,
    canonical_product_key VARCHAR NOT NULL,
    relevance_rank INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (eval_query_id, canonical_product_key)
);

CREATE TABLE IF NOT EXISTS app.eval_runs (
    eval_run_id VARCHAR PRIMARY KEY,
    index_run_id VARCHAR,
    strategy_version VARCHAR NOT NULL,
    embedding_model VARCHAR NOT NULL,
    k INTEGER NOT NULL,
    hit_at_k DOUBLE NOT NULL,
    recall_at_k DOUBLE NOT NULL,
    mrr DOUBLE,
    created_at TIMESTAMP DEFAULT now()
);
