#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"
CSV_PATH="${2:-data/IKEA_product_catalog.csv}"

./scripts/init_duckdb.sh "${DB_PATH}"
./scripts/load_ikea_data.sh "${DB_PATH}" "${CSV_PATH}"

uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first

echo "Phase 1 data/index pipeline complete. Start web app with:"
echo "  uv run python -m tal_maria_ikea.web.runserver"
