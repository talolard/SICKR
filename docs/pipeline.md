# Phase 2 Pipeline Runbook

## End-to-End Steps
1. Initialize DB schema and baseline views:
   - `./scripts/init_duckdb.sh`
2. Load and model catalog data:
   - `./scripts/load_ikea_data.sh`
3. Build embeddings (sync-first, parallel, single strategy-free path):
   - `uv run python -m tal_maria_ikea.ingest.index`
   - Optional VSS index build:
     `uv run python -m tal_maria_ikea.ingest.index --build-vss-index`
   - Or explicit index script:
     `./scripts/build_vss_index.sh data/ikea.duckdb cosine`
4. Run local Django search UI:
   - `uv run python -m tal_maria_ikea.web.runserver`
5. Run eval loop (after labels exist):
   - `uv run python -m tal_maria_ikea.eval.run --index-run-id latest --k 10`

For local greenfield setup, `make init` is the canonical bootstrap and resets the DB.

## Module Layout
- `src/tal_maria_ikea/shared/` typed contracts + DB/parsing helpers
- `src/tal_maria_ikea/ingest/` embedding repository and indexing CLI
- `src/tal_maria_ikea/retrieval/` retrieval and shortlist services
- `src/tal_maria_ikea/web/` Django forms/views/routes/templates
- `src/tal_maria_ikea/eval/` query generation and metrics runner

## SQL Layout
- `sql/10_schema.sql` core tables
- `sql/11_profile_source.sql` source profiling
- `sql/12_model_canonical.sql` Germany canonical modeling
- `sql/13_mapping_tables.sql` quality/mapping analytics
- `sql/14_market_views.sql` phase market view
- `sql/15_description_rollup.sql` product description by country rollup
- `sql/21_embedding_inputs.sql` single embedding input view
- `sql/22_embedding_store.sql` embedding storage view
- `sql/23_parquet_exports.sql` parquet artifact exports
- `sql/31_retrieval_candidates.sql` retrieval query
- `sql/32_shortlist.sql` shortlist hydration query
- `sql/41_eval_registry.sql` eval registry view

## Vector Similarity Notes
- Retrieval SQL uses `array_cosine_distance` over `FLOAT[EMBEDDING_DIMENSIONS]`
  vectors (default `256`).
- Optional HNSW index support uses DuckDB `vss` extension.
- Reference doc: `external_docs/duckdb_vector_similarity.md`.

## Operational Note: Embedding Dimensions
- Large fixed vectors (for example `3072`) significantly increase DuckDB upsert cost.
- If indexing appears stalled after embedding API calls, reduce `EMBEDDING_DIMENSIONS`
  and rerun indexing.

## Rate-Limit Handling
- Indexing retries embedding chunks on provider errors (including quota 429).
- Retry delay parsing uses Gemini-provided hints when available (`retry in Xs`, `retryDelay`).
- Backoff is bounded and configurable via `EMBEDDING_*RETRY*` settings.

## Typed Boundaries
Key contracts are defined in `src/tal_maria_ikea/shared/types.py`, including:
- retrieval request/result + filter objects
- embedding input/vector rows
- shortlist state
- evaluation metric/result objects

## Parquet Artifacts
- Default artifact root: `data/parquet/`
- Exported datasets:
  - `products_raw` partitioned by `country`
  - `products_canonical` partitioned by `country`
  - `product_embeddings`
  - `product_description_country_rollup`
- Git policy note: parquet files are local artifacts for iteration; do not commit them until Git LFS policy is set.
