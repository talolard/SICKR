#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"
CSV_PATH="${2:-data/IKEA_product_catalog.csv}"
DELETE_RAW="${DELETE_RAW:-0}"

if [[ ! -f "${CSV_PATH}" ]]; then
  echo "Missing CSV: ${CSV_PATH}" >&2
  exit 1
fi

CSV_PATH="${CSV_PATH}" duckdb "${DB_PATH}" < sql/20_load_raw.sql
duckdb "${DB_PATH}" < sql/12_model_canonical.sql
duckdb "${DB_PATH}" < sql/14_market_views.sql
duckdb "${DB_PATH}" < sql/21_embedding_inputs.sql

echo "Loaded IKEA catalog into ${DB_PATH}"

if [[ "${DELETE_RAW}" == "1" ]]; then
  rm -f "${CSV_PATH}"
  echo "Deleted raw CSV ${CSV_PATH}"
fi
