# Phase 1 Pipeline Runbook

## End-to-End Steps
1. Initialize DB schema and baseline views:
   - `./scripts/init_duckdb.sh`
2. Load and model catalog data:
   - `./scripts/load_ikea_data.sh`
3. Build embeddings (sync-first, parallel):
   - `uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first`
   - Optional VSS index build:
     `uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first --build-vss-index`
   - Or explicit index script:
     `./scripts/build_vss_index.sh data/ikea.duckdb cosine`
4. Run local Django search UI:
   - `uv run python -m tal_maria_ikea.web.runserver`
5. Run eval loop (after labels exist):
   - `uv run python -m tal_maria_ikea.eval.run --index-run-id latest --k 10`

## Module Layout
- `src/tal_maria_ikea/shared/` typed contracts + DB/parsing helpers
- `src/tal_maria_ikea/ingest/` embedding strategies, repository, indexing CLI
- `src/tal_maria_ikea/retrieval/` retrieval and shortlist services
- `src/tal_maria_ikea/web/` Django forms/views/routes/templates
- `src/tal_maria_ikea/eval/` query generation and metrics runner

## SQL Layout
- `sql/10_schema.sql` core tables
- `sql/11_profile_source.sql` source profiling
- `sql/12_model_canonical.sql` Germany canonical modeling
- `sql/13_mapping_tables.sql` quality/mapping analytics
- `sql/14_market_views.sql` phase market view
- `sql/21_embedding_inputs.sql` text strategy views
- `sql/22_embedding_store.sql` embedding storage view
- `sql/31_retrieval_candidates.sql` retrieval query
- `sql/32_shortlist.sql` shortlist hydration query
- `sql/41_eval_registry.sql` eval registry view

## Vector Similarity Notes
- Retrieval SQL uses `array_cosine_distance` over `FLOAT[3072]` vectors.
- Optional HNSW index support uses DuckDB `vss` extension.
- Reference doc: `external_docs/duckdb_vector_similarity.md`.

## Typed Boundaries
Key contracts are defined in `src/tal_maria_ikea/shared/types.py`, including:
- retrieval request/result + filter objects
- embedding input/vector rows
- shortlist state
- evaluation metric/result objects
