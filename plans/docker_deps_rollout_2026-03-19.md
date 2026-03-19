# Docker Dependency Rollout Implementation Plan

Date: 2026-03-19

## Goal

Land the Docker dependency rollout umbrella `tal_maria_ikea-deh` in one branch by
moving local runtime dependencies from copied DuckDB and Milvus Lite files to:

- one global Dockerized Milvus service
- one worktree-local Dockerized Postgres service
- Postgres-backed catalog, app, and ops schemas
- explicit seed and refresh flows
- Postgres-backed image catalog metadata

## Current Constraints

- The worktree bootstrap still copies DuckDB and Milvus Lite files into
  `.tmp_untracked/runtime`.
- This worktree does not contain `data/ikea.duckdb`, so the legacy bootstrap
  contract is already brittle.
- Checked-in canonical catalog inputs live under `data/parquet/`.
- The canonical local image catalog lives under
  `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`.
- Runtime queries, migrations, and tests still assume DuckDB parameter and URL
  conventions in several places.

## Target Contract

### Bootstrap

Bootstrap will:

1. ensure the global Milvus Compose stack is healthy
2. ensure the slot-scoped Postgres Compose stack is healthy
3. seed empty Postgres volumes from canonical parquet and image-catalog inputs
4. run Alembic migrations to head
5. write `.tmp_untracked/worktree.env` with `DATABASE_URL`, shared `MILVUS_URI`,
   slot ports, and local artifact roots

Bootstrap will not copy any DuckDB or Milvus files into the worktree.

### Storage boundaries

- `catalog` schema: seeded product rows, embedding snapshot rows, embedding
  neighbor rows, and image catalog metadata
- `app` schema: mutable runtime and user state
- `ops` schema: seed and refresh metadata for Postgres and Milvus

### Seed sources

- Product metadata: `data/parquet/products_canonical`
- Embedding snapshot rows: `data/parquet/product_embeddings`
- Image catalog metadata: shared image catalog outputs under
  `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`
- Milvus vectors: hydrated from the seeded Postgres embedding snapshot

## Execution order

1. Epic 1: add Compose definitions, slot/global dependency helpers, bootstrap
   orchestration, and make targets
2. Epic 2: switch runtime and migrations to `DATABASE_URL`, Postgres-native
   schema ownership, and explicit `catalog` / `app` / `ops` boundaries
3. Epic 3: add repeatable Postgres and Milvus prepare/reseed flows plus seed
   metadata and failure semantics
4. Epic 4: centralize Milvus into the global service and remove opportunistic
   hydration from normal startup
5. Epic 5: move image catalog metadata into Postgres and remove runtime DuckDB
   image lookups
6. Epic 6: make image serving configurable and future-storage-aware
7. Epic 7: update docs, add smoke coverage, run the end-state acceptance sweep,
   and open corrective follow-ups only if failures remain

## Validation

Required before closeout:

- `make tidy`
- targeted backend tests while implementation is in flight
- `make ui-test-e2e-real-ui-smoke` after runtime/image changes settle
- explicit acceptance notes covering end states 1 through 15 from
  `specs/docker-deps/target-state-spec.md`
