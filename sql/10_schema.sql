-- Base schema for local analytics and semantic search scaffolding.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.products_raw (
    source_row_id BIGINT,
    payload JSON,
    ingested_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.products (
    product_id VARCHAR PRIMARY KEY,
    product_name VARCHAR NOT NULL,
    category VARCHAR,
    description VARCHAR,
    dimensions_text VARCHAR,
    price_text VARCHAR,
    currency VARCHAR,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.product_embeddings (
    product_id VARCHAR PRIMARY KEY,
    embedding_model VARCHAR NOT NULL,
    embedding_json JSON NOT NULL,
    embedded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.query_log (
    query_id VARCHAR PRIMARY KEY,
    query_text VARCHAR NOT NULL,
    query_limit INTEGER NOT NULL,
    request_source VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);
