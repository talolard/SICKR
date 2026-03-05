#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"
CSV_PATH="${2:-data/IKEA_product_catalog.csv}"

./scripts/init_duckdb.sh "${DB_PATH}"
./scripts/load_ikea_data.sh "${DB_PATH}" "${CSV_PATH}"

uv run python -m ikea_agent.ingest.index
# Optional: append --build-vss-index to create HNSW index via DuckDB vss extension.

echo "Phase 1 data/index pipeline complete. Start web app with:"
echo "  uv run python -m ikea_agent.web.runserver"
