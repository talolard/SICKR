"""Inline schema bootstrap for the active ikea_agent runtime."""

from __future__ import annotations

import duckdb


def ensure_runtime_schema(connection: duckdb.DuckDBPyConnection) -> None:
    """Create the minimal DuckDB schema required by active runtime paths."""

    connection.execute("CREATE SCHEMA IF NOT EXISTS app")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app.products_canonical (
            canonical_product_key VARCHAR PRIMARY KEY,
            product_id BIGINT,
            unique_id VARCHAR,
            country VARCHAR,
            product_name VARCHAR,
            product_type VARCHAR,
            description_text VARCHAR,
            main_category VARCHAR,
            sub_category VARCHAR,
            dimensions_text VARCHAR,
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
            source_updated_at TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app.product_embeddings (
            canonical_product_key VARCHAR,
            embedding_model VARCHAR,
            run_id VARCHAR,
            embedding_vector FLOAT[],
            embedded_text VARCHAR,
            embedded_at TIMESTAMP,
            PRIMARY KEY (canonical_product_key, embedding_model)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app.query_log (
            query_id VARCHAR PRIMARY KEY,
            query_text VARCHAR,
            sort_mode VARCHAR,
            include_keyword VARCHAR,
            exclude_keyword VARCHAR,
            result_limit BIGINT,
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
            low_confidence BOOLEAN,
            request_source VARCHAR,
            latency_ms BIGINT,
            created_at TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app.shortlist_global (
            canonical_product_key VARCHAR PRIMARY KEY,
            added_at TIMESTAMP,
            note VARCHAR
        )
        """
    )
