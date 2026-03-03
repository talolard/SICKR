#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/ikea.duckdb}"
METRIC="${2:-cosine}"

duckdb "${DB_PATH}" <<SQL
INSTALL vss;
LOAD vss;
SET hnsw_enable_experimental_persistence = true;
CREATE INDEX IF NOT EXISTS idx_product_embeddings_hnsw
ON app.product_embeddings
USING HNSW (embedding_vector)
WITH (metric='${METRIC}');
SQL

echo "VSS HNSW index ready on ${DB_PATH} with metric=${METRIC}"
