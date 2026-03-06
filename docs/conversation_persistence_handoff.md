# Conversation Persistence Implementation Handoff Log

This file is the continuity log for the conversation persistence epic and all child tasks.

## Protocol
- At task start: read this file fully.
- At task end: append a dated entry to `## Progress Log` including:
  - task id and title
  - what changed (code, schema, routes, docs, tests)
  - migrations created/updated
  - commands/tests run and results
  - risks, known gaps, and follow-up notes
  - exact next-step recommendation for the next task

## Progress Log

### 2026-03-06 - Epic and subtask scaffold created
- Created initial epic and subtasks in Beads for durable conversation persistence, asset storage metadata, and UI-queryable thread data.
- Established this file as required start/end handoff checkpoint for every related task.
- Next step: claim first subtask and begin schema + migration scaffolding.

### 2026-03-06 - Task `tal_maria_ikea-l18.1` completed
- Read this file at task start.
- Added SQLAlchemy/Alembic foundation:
  - Dependencies in `pyproject.toml` and `uv.lock` (`sqlalchemy`, `alembic`, `duckdb-engine`).
  - SQLAlchemy DB helper module:
    - `src/ikea_agent/shared/sqlalchemy_db.py`
  - Alembic DuckDB impl shim:
    - `src/ikea_agent/shared/alembic_duckdb.py`
  - Alembic scaffold files:
    - `alembic.ini`
    - `migrations/env.py`
    - `migrations/script.py.mako`
    - `migrations/versions/20260306_0001_migration_foundation.py`
    - `migrations/README`
  - Package markers for lint/import hygiene:
    - `migrations/__init__.py`
    - `migrations/versions/__init__.py`
- Added initial runtime wiring:
  - `src/ikea_agent/chat/runtime.py` now creates/stores a SQLAlchemy DuckDB engine (`ChatRuntime.sqlalchemy_engine`).
- Added migration docs:
  - `docs/data/migrations.md`
  - linked from `docs/index.md` and `docs/data/index.md`.
- Added tests:
  - `tests/shared/test_sqlalchemy_db.py`
  - `tests/shared/__init__.py`
- Migrations created/updated:
  - Created base Alembic revision `20260306_0001` (foundation no-op revision).
- Commands/tests run:
  - `uv lock` (updated lockfile with new deps)
  - `uv sync --all-groups`
  - `uv run ruff check src/ikea_agent/chat/runtime.py src/ikea_agent/shared/sqlalchemy_db.py src/ikea_agent/shared/alembic_duckdb.py tests/shared/test_sqlalchemy_db.py migrations/env.py migrations/versions/20260306_0001_migration_foundation.py`
  - `uv run pytest tests/shared/test_sqlalchemy_db.py -q` (2 passed)
  - `ALEMBIC_DATABASE_URL="duckdb:///$(pwd)/.tmp_untracked/alembic_validation.duckdb" uv run alembic upgrade head` (succeeded)
- Risks / known gaps:
  - Alembic uses a custom DuckDB impl shim based on PostgreSQL implementation; broad DDL edge cases will need validation as schema complexity increases.
  - Runtime still uses legacy raw-SQL retrieval repositories; conversion is next task scope.
  - Full `make tidy` was not run at this stage to avoid reformatting unrelated in-progress work already present in the working tree.
- Next step recommendation:
  - Claim `tal_maria_ikea-l18.2` and introduce SQLAlchemy models + migrations for thread/run/asset/analysis/search persistence tables.

### 2026-03-06 - Task `tal_maria_ikea-l18.2` completed
- Read this file at task start.
- Added SQLAlchemy persistence models:
  - `src/ikea_agent/persistence/models.py`
  - `src/ikea_agent/persistence/__init__.py`
- Wired Alembic metadata target to persistence models:
  - `migrations/env.py` now imports `Base.metadata`.
- Added migration revision creating durable persistence tables:
  - `migrations/versions/20260306_0002_conversation_persistence_tables.py`
  - Tables created under `app` schema:
    - `threads`, `agent_runs`, `message_archives`, `assets`, `floor_plan_revisions`,
      `analysis_runs`, `analysis_detections`, `search_runs`, `search_results`
  - Includes ownership field (`owner_id`) for single-user-now / multi-user-ready scope.
- Added migration validation test:
  - `tests/shared/test_migrations.py`
- Migrations created/updated:
  - Added `20260306_0002` revision on top of `20260306_0001`.
  - Updated `alembic.ini` (`path_separator = os`) and `migrations/env.py` DB URL resolution to respect CLI-configured URL.
- Commands/tests run:
  - `uv run ruff check src/ikea_agent/persistence/models.py migrations/env.py migrations/versions/20260306_0002_conversation_persistence_tables.py tests/shared/test_migrations.py`
  - `uv run pytest tests/shared/test_migrations.py tests/shared/test_sqlalchemy_db.py -q` (3 passed)
  - `ALEMBIC_DATABASE_URL="duckdb:///$(pwd)/.tmp_untracked/alembic_validation_l18_2.duckdb" uv run alembic upgrade head` (succeeded)
- Risks / known gaps:
  - JSON payload columns are text for portability in this phase; typed JSON operators are not yet leveraged.
  - Runtime read/write paths are not yet switched to these tables; integration starts in next tasks.
- Next step recommendation:
  - Claim `tal_maria_ikea-l18.3` and migrate active runtime retrieval/bootstrap SQL paths to SQLAlchemy wiring.

### 2026-03-06 - Task `tal_maria_ikea-l18.3` completed
- Read this file at task start.
- Migrated active runtime retrieval/bootstrap paths to SQLAlchemy-managed access:
  - Added retrieval SQLAlchemy table definitions:
    - `src/ikea_agent/retrieval/schema.py`
  - Replaced bootstrap raw DuckDB DDL execution with SQLAlchemy metadata create flow:
    - `src/ikea_agent/shared/bootstrap.py`
  - Refactored retrieval repositories from direct DuckDB connection usage to SQLAlchemy engine usage:
    - `src/ikea_agent/retrieval/catalog_repository.py`
  - Updated chat runtime wiring to SQLAlchemy-managed primitives:
    - `src/ikea_agent/chat/runtime.py`
    - `ChatRuntime` now stores `sqlalchemy_engine` + `session_factory`; active runtime no longer relies on raw DuckDB connection field.
- Updated retrieval tests for SQLAlchemy engine-backed setup:
  - `tests/retrieval/test_repository.py`
- Migrations created/updated:
  - No new migration revision for this task.
- Commands/tests run:
  - `uv run ruff check src/ikea_agent/retrieval/schema.py src/ikea_agent/shared/bootstrap.py src/ikea_agent/retrieval/catalog_repository.py src/ikea_agent/chat/runtime.py tests/retrieval/test_repository.py`
  - `uv run pytest tests/retrieval/test_repository.py tests/chat/test_runtime.py -q` (5 passed)
- Risks / known gaps:
  - Retrieval hydration still uses raw SQL text statements executed through SQLAlchemy driver API for parity and temp-table semantics; full query-builder conversion can be done incrementally later.
  - Legacy helper `src/ikea_agent/shared/db.py` remains for non-runtime scripts and is not part of active runtime retrieval path.
- Next step recommendation:
  - Claim `tal_maria_ikea-l18.4` and persist AG-UI run lifecycle + message archive records from live runs.

### 2026-03-06 - Task `tal_maria_ikea-l18.4` completed
- Read this file at task start.
- Added durable AG-UI run lifecycle persistence wiring:
  - `src/ikea_agent/chat_app/main.py`
  - Replaced `app.mount("/ag-ui", web_agent.to_ag_ui(...))` with explicit `/ag-ui` POST handlers that delegate to `handle_ag_ui_request(...)` and attach `on_complete` callback.
  - Persist run start (`started`), completion (`completed`), and failure (`failed`) states.
  - Parse AG-UI payload for `thread_id`, `run_id`, `parent_run_id`, and user prompt extraction.
- Added repository for lifecycle + archive persistence:
  - `src/ikea_agent/persistence/run_history_repository.py`
  - Methods: `record_run_start`, `record_run_complete`, `record_run_failed`, `load_archived_all_messages_json`.
  - Added `extract_last_user_prompt` helper for AG-UI payloads.
- Added persistence tests:
  - `tests/persistence/test_run_history_repository.py`
  - `tests/persistence/__init__.py`
- Added schema bootstrap helper used by app startup:
  - `src/ikea_agent/persistence/models.py` with `ensure_persistence_schema(engine)`.
- Added package docstrings required by lint quality gate:
  - `migrations/__init__.py`
  - `migrations/versions/__init__.py`
  - `tests/shared/__init__.py`
- While running mandatory `make tidy`, fixed two typed SQLAlchemy migration regressions caught by `pyrefly`:
  - `src/ikea_agent/retrieval/catalog_repository.py` (typed row casting + semantic score narrowing)
  - `src/ingest/hydrate_milvus.py` (switch to SQLAlchemy engine helper)
- Migrations created/updated:
  - No new migration revision for this task.
- Commands/tests run:
  - `uv run ruff check src/ikea_agent/chat_app/main.py src/ikea_agent/persistence/models.py src/ikea_agent/persistence/run_history_repository.py tests/persistence/test_run_history_repository.py tests/chat/test_api.py`
  - `uv run pytest tests/persistence/test_run_history_repository.py tests/chat/test_api.py -q` (8 passed)
  - `make tidy` (passed; 54 tests passed)
- Risks / known gaps:
  - Resume path reconstruction API is repository-ready (`load_archived_all_messages_json`) but not yet exposed via explicit runtime resume endpoint/tool selection flag.
  - AG-UI payload parsing is tolerant/best-effort; malformed payloads log debug and proceed with normal AG-UI flow.
- Next step recommendation:
  - Claim `tal_maria_ikea-l18.5` and migrate attachment/generated artifact storage to durable filesystem + `assets` table metadata linkage.
