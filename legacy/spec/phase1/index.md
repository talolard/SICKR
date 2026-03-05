# Phase 1 Implementation Plan (Spec-Driven, Sequence-Locked)

## Summary
Implement Phase 1 exactly in the existing sequence (`1`→`6`), and first **expand the current `spec/phase1/*.md` files into decision-complete implementation specs** so execution is unambiguous for agents.

This plan is now locked to your choices:
- Embeddings: **native numeric vector storage** (DuckDB array/vector style), not JSON.
- Eval labeling: **Top-3 expected set**.
- UI: **include shortlist with persistence** and **single global shortlist** (no auth/session isolation).
- Indexing: **sync-first**, with batching as explicit opt-in.
- Sync indexing must use **parallelism** (multi-item per call where possible + concurrent calls).
- Gemini backend: **Vertex AI (standard GCP flow)**.
- Default embedding model: **`gemini-embedding-001`**.
- Retrieval filters: **category + price + dimensions**.
- Price filtering: **EUR numeric only**, with explicit placeholder for future currency normalization.
- Dimensions filtering: numeric behavior; implement optional exact/range/max per provided dimensions.

---

## Scope and Sequence
1. Data audit + Germany-scoped canonical modeling  
2. Embedding text strategy + indexing job  
3. Retrieval service contract + vector search  
4. Django web app + persisted shortlist  
5. Eval set generation + metrics loop  
6. Integration hardening + phase exit checklist

No phase-jumping. Each phase must satisfy its own exit criteria before moving on.

---

## Planned Spec File Extensions (first step before coding)
Extend these files with concrete sections: schema, interfaces, CLI, error handling, tests, acceptance criteria.
- `spec/phase1/1_data_and_db.md`
- `spec/phase1/2_embedding_pipeline.md`
- `spec/phase1/3_retrieval_service.md`
- `spec/phase1/4_django_web_app.md`
- `spec/phase1/5_eval_set_and_metrics.md`
- `spec/phase1/6_integration_and_exit.md`
- `spec/phase1/index.md` (cross-phase dependency table + artifact map)

Each file gets:
- Inputs/outputs
- Module/file-level implementation map
- SQL object definitions (tables/views/indexes)
- CLI contract
- Typed contract definitions
- Deterministic tests
- Exit checklist

---

## Public Interfaces and Type Changes

### 1) Shared typed contracts (`src/ikea_agent/shared/types.py`)
Add/replace with explicit dataclasses and literals:
- `MarketCode = Literal["DE"]` (phase 1 locked)
- `EmbeddingStrategyVersion = Literal["v1_baseline", "v2_metadata_first"]`
- `EmbeddingProvider = Literal["vertex_gemini"]`
- `DimensionFilter` with optional `exact_cm`, `min_cm`, `max_cm` per axis (`width`, `depth`, `height`)
- `PriceFilterEUR` with `min_eur`, `max_eur`
- `RetrievalFilters` (`category`, `price`, `dimensions`)
- `RetrievalRequest` and `RetrievalResult`
- `ShortlistItem`, `ShortlistState`
- `EvalQuery`, `EvalLabelSet`, `EvalRunMetrics`

### 2) Retrieval service interface (`src/ikea_agent/retrieval/service.py`)
- `retrieve(request: RetrievalRequest) -> list[RetrievalResult]`
- Stable scoring fields:
  - `semantic_score`
  - `filter_pass_reasons`
  - `rank_explanation` (short text)

### 3) Ingest/index CLI interfaces
- `python -m ikea_agent.ingest.index run --scope germany --strategy v2_metadata_first --subset-limit N --parallelism M`
- `--use-batch` optional, not default.

### 4) Eval CLI interfaces
- Generate eval queries:
  - `python -m ikea_agent.eval.generate --subset-id ... --prompt-version ... --target-count 200`
- Run eval:
  - `python -m ikea_agent.eval.run --index-run-id ... --k 10`

### 5) Web UI contract
- Search endpoint with structured filter form inputs:
  - query text
  - category
  - min/max EUR
  - optional width/depth/height exact/min/max
- Shortlist endpoints:
  - add/remove/list (global shortlist table)

---

## Data and SQL Plan

### Phase 1 SQL objects (new/expanded under `sql/`)
- `sql/11_profile_source.sql`: nulls, duplicates, country distributions, DE quality report.
- `sql/12_model_canonical.sql`:
  - canonical products table (DE-scoped materialized layer)
  - parsed numeric dimensions columns
  - parsed `price_eur` numeric
- `sql/13_mapping_tables.sql`:
  - product family / duplicate alias mapping
  - unresolved collision table
- `sql/14_market_views.sql`:
  - `app.products_market_de_v1`
  - market switch abstraction (single SQL definition point)
- `sql/21_embedding_inputs.sql`:
  - embedding text materialization by strategy version
- `sql/22_embedding_store.sql`:
  - vectors + metadata (`model`, `strategy_version`, `run_id`, timestamps)
- `sql/31_retrieval_candidates.sql`:
  - vector similarity + hydration + filter application
- `sql/32_shortlist.sql`:
  - global shortlist persistence table
- `sql/41_eval_registry.sql`:
  - prompt registry, subset registry, generated queries, labels, metric snapshots

---

## Implementation Details by Sequence

### 1. Data + DB
- Profile raw dataset and lock DE filter logic.
- Normalize to canonical DE table with deterministic primary key strategy.
- Parse dimensions and EUR numeric price into typed columns.
- Maintain alias/family mapping tables for duplicates and grouped IDs.
- Update `docs/data/index.md` and create `docs/data/data_patterns.md`.

### 2. Embedding pipeline
- Implement strategy abstraction:
  - `v1_baseline`: name + description
  - `v2_metadata_first`: structured metadata header + body text
- Sync-first indexer:
  - chunk records
  - send many contents per request where API allows
  - parallel requests via bounded worker pool
- Optional `--use-batch` mode for experiments.
- Idempotent upsert keyed by `(product_key, model, strategy_version)` plus run metadata table.
- Detailed progress logging (`run_id`, completed/total, throughput, ETA approximation).

### 3. Retrieval service
- Query embedding with same model family and explicit query task type.
- Candidate retrieval via SQL similarity + structured filters.
- Safeguards: max limit cap, empty-result handling, low-confidence threshold path.
- Persist query log with request/latency/filter metadata.

### 4. Django web app
- Build CBV-based search page + paginated results.
- Add filter controls for category/price/dimensions.
- Implement persisted shortlist (global list).
- Add local debug toggles and operational docs.
- Keep runtime retrieval-only (no indexing in web process).

### 5. Eval loop
- Gemini structured-output generator for candidate queries with provenance.
- Curate final 200-query set with expected top-3 labels.
- Metrics: `Hit@k`, `Recall@k`, optional `MRR`.
- Strategy comparison reports (`v1` vs `v2`) with selection note.

### 6. Integration + phase exit
- Single runbook: init DB → load/model → index → run web → eval.
- Add smoke/integration tests across CLI + retrieval + web response path.
- Produce final phase status matrix (`done/partial/deferred`) and phase-2 backlog.

---

## Testing Plan (must pass per phase)
- Unit tests:
  - text strategy builders
  - dimension/price parsers
  - retrieval filter logic
  - shortlist repository operations
  - eval metric functions
- SQL validation tests:
  - DE scope row counts
  - uniqueness guarantees
  - mapping table consistency
- Integration tests:
  - subset indexing run end-to-end
  - retrieval returns hydrated canonical rows
  - Django search + shortlist persistence flow
- Regression checks:
  - stable typed contracts
  - no untyped leaks (pyrefly gate)
  - deterministic eval run outputs for fixed fixture subset

---

## Docs and Runbook Outputs
- `docs/pipeline.md`: concrete phase execution runbook.
- `docs/typing.md`: extend with new package typing rules.
- `docs/data/index.md` + `docs/data/data_patterns.md`: canonical schema and observed data quirks.
- `docs/web.md` (new): UI routes, filters, shortlist behavior.
- `docs/eval.md` (new): provenance schema + metric interpretation.

---

## Ambiguities and Inputs Needed From You

### Already resolved by your inputs (locked)
- Storage, model, backend, filters, shortlist persistence mode, eval depth, sync-first parallel indexing.

### Remaining small ambiguities to confirm during implementation
1. Global shortlist conflict policy: if same product is added twice, should we de-duplicate or count additions?  
Default in plan: **de-duplicate by product key**.
2. Dimension filter precedence when both exact and range are provided on same axis.  
Default in plan: **exact takes precedence; range ignored for that axis with validation warning**.
3. Low-confidence behavior in retrieval UI.  
Default in plan: **show results plus “low confidence” banner**, not hard-empty.

---

## Assumptions and Defaults
- Germany scoping means `country = 'Germany'` in source data.
- Price filtering is applied on parsed numeric EUR value only.
- Dimension parsing targets cm values from `product_measurements`; unparsable rows remain searchable but are excluded from strict numeric dimension filters.
- No auth/user model is added in Phase 1.
- Batch embedding remains optional and non-blocking for successful indexing runs.
