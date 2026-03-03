#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"

duckdb "${DB_PATH}" < sql/00_pragmas.sql
duckdb "${DB_PATH}" < sql/10_schema.sql
duckdb "${DB_PATH}" < sql/14_market_views.sql
duckdb "${DB_PATH}" < sql/21_embedding_inputs.sql
duckdb "${DB_PATH}" < sql/22_embedding_store.sql
duckdb "${DB_PATH}" < sql/41_eval_registry.sql

echo "Initialized DuckDB at ${DB_PATH}"
