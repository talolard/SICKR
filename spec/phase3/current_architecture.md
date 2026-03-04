# Phase 3 Current Architecture (As-Is)

This document captures the current repository architecture before Phase 3 implementation.

## Scope and Runtime Shape

The current application is a local-first semantic search stack with four primary slices:

1. Data modeling + retrieval store in DuckDB.
2. Embedding and eval tooling in Python CLI modules.
3. Django web UI for local interaction.
4. Lightweight structured logging via `structlog`.

There is no authentication layer, no async job queue, and no background worker process in the current runtime.

## Major Modules and Responsibilities

### Retrieval runtime

- `src/tal_maria_ikea/retrieval/service.py`
  - Orchestrates query embedding + retrieval + query logging.
  - Embeds each query with Gemini (`VertexGeminiEmbeddingClient`).
  - Runs retrieval through `RetrievalRepository`.
  - Logs retrieval request metadata to `app.query_log`.
- `src/tal_maria_ikea/retrieval/repository.py`
  - Executes retrieval SQL from `sql/31_retrieval_candidates.sql`.
  - Applies structured filters after nearest-neighbor candidate fetch.
  - Persists query logs and shortlist rows.
- `src/tal_maria_ikea/retrieval/shortlist_service.py`
  - Provides global shortlist add/remove/list behavior.

### Web runtime (Django)

- `src/tal_maria_ikea/web/views.py`
  - `SearchView`: GET-based query + filters + result rendering.
  - `StatsView`: basic data counts from DuckDB.
  - `ShortlistAddView` / `ShortlistRemoveView`: shortlist writes.
- `src/tal_maria_ikea/web/forms.py`
  - `SearchForm` defines query and filter controls.
- `src/tal_maria_ikea/web/templates/web/search.html`
  - Main search UX, filter chips, pagination, shortlist panel.
- `src/tal_maria_ikea/web/project/settings.py`
  - Django configured with SQLite (`data/django.sqlite3`) as Django DB.
  - Current app does not define Django models/admin entities.

### Ingest + eval tooling

- `src/tal_maria_ikea/ingest/index.py` and related ingest modules build embeddings.
- `src/tal_maria_ikea/eval/*` provides eval query generation, labels bootstrap, and metrics.
- Eval registry currently persists prompt/subset/run metadata in DuckDB tables (e.g. `app.eval_prompt_registry`).

### Shared foundation

- `src/tal_maria_ikea/shared/types.py`: typed dataclasses for retrieval and eval boundaries.
- `src/tal_maria_ikea/config.py`: typed env-driven runtime settings.
- `src/tal_maria_ikea/shared/db.py`: DuckDB connection and SQL file runner helpers.

## Data Stores and State Boundaries

The current codebase already uses two persistent stores with distinct purposes.

## 1) DuckDB (`data/ikea.duckdb`)

Primary analytics/retrieval store.

Current important tables/views:

- Product and modeling layer:
  - `app.products_raw`
  - `app.products_canonical`
  - `app.products_market_de_v1`
- Embeddings and retrieval:
  - `app.embedding_runs`
  - `app.product_embeddings`
  - `app.product_embeddings_latest` (view)
  - `app.query_log`
- UX persistence:
  - `app.shortlist_global`
- Eval registries:
  - `app.eval_prompt_registry`
  - `app.eval_subset_registry`
  - `app.eval_queries_generated`
  - `app.eval_labels`
  - `app.eval_runs`

## 2) Django SQLite (`data/django.sqlite3`)

Current role is framework-operational only (sessions/messages/contenttypes). No domain models yet.

## Current End-to-End Search Flow

1. User sends GET request to `/` with query + optional filters.
2. `SearchForm` validates input.
3. `SearchView` builds `RetrievalRequest`.
4. `RetrievalService` embeds query text with Gemini embedding model.
5. `RetrievalRepository.search()` runs vector retrieval + structured filtering SQL.
6. Service logs query metadata to `app.query_log`.
7. View paginates and renders results + active filter chips.
8. Optional shortlist actions write to `app.shortlist_global`.

## Existing Observability

- Structured logs are emitted via `structlog`.
- Query-level retrieval metadata is persisted in DuckDB (`app.query_log`).
- There is no persisted prompt-run lineage for user-facing generations.
- There is no persisted conversation thread model.
- There is no user feedback/rating capture path.

## Current Strengths

1. SQL-first retrieval pipeline and schema management are already established.
2. Typed service boundary for retrieval request/response exists.
3. Local runbook and quality tooling are in place (`make tidy`, `make test`).
4. Existing eval prompt registry patterns can be reused for Phase 3 provenance.

## Current Gaps Relative to Phase 3

1. No reranking step; only semantic candidate ranking + simple sort modes.
2. No Gemini summary/recommendation workflow in UI request path.
3. No system prompt template management surface.
4. No conversation thread persistence and follow-up turns.
5. No query expansion and no explicit expansion controls.
6. No before/after ranking snapshot persistence for analysis.
7. No turn-level/item-level user feedback capture.
8. No prompt variant comparison screen or parallel variant execution.

## Constraints and Design Implications

1. Local M1 workflow is the primary development target.
2. Two-DB architecture is retained for Phase 3:
   - DuckDB remains runtime analytics + retrieval store.
   - Django SQLite is used for admin-managed prompt/config entities.
3. Query-time features must preserve responsiveness in local mode.
4. Added model/runtime dependencies should prefer small footprint and robust fallback behavior.

## Architecture Direction for Phase 3

Phase 3 will extend the current architecture rather than replacing it:

1. Add new service modules for expansion, reranking, prompt execution, conversations, and ratings.
2. Keep retrieval results and event telemetry in DuckDB for analysis.
3. Add minimal Django model/admin layer for prompt templates and feedback reason taxonomies.
4. Add new web routes/views/templates for prompt comparison, rerank diff visualization, and threaded follow-ups.
5. Maintain reproducible provenance by storing prompt templates/version/hash and model outputs per run.
