#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"

duckdb "${DB_PATH}" < sql/00_pragmas.sql
duckdb "${DB_PATH}" < sql/10_schema.sql

echo "Initialized DuckDB at ${DB_PATH}"
