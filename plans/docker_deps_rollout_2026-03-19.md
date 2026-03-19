# Docker Dependency Rewrite Plan

Date: 2026-03-19

## Goal

Track the rewrite requested on PR #69 after the architecture correction.

The corrected target is no longer:

- Postgres plus one shared Milvus service

The corrected target is:

- one worktree-local Dockerized Postgres service
- Postgres-backed `catalog`, `app`, and `ops` schemas
- `pgvector` for vector retrieval inside Postgres
- explicit snapshot creation locally and in CI
- snapshot restore during normal bootstrap
- Postgres-backed image catalog metadata
- no active Milvus or DuckDB runtime path

This plan now tracks rewrite epic `tal_maria_ikea-5p1`.

## Current Constraints

- PR #69 landed a transitional design that still keeps Milvus in the active
  runtime/dependency path.
- The current retrieval path is still split between vector candidate lookup and
  relational hydration/filtering.
- Snapshot restore is required for developer ergonomics, but snapshot creation
  was not previously specified as a first-class workflow.
- Active runtime and tooling still expose DuckDB compatibility in several
  places.
- Checked-in canonical catalog inputs live under `data/parquet/`.
- The canonical local image catalog lives under
  `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`.

## Target Contract

### Bootstrap

Bootstrap will:

1. ensure the slot-scoped Postgres Compose stack is healthy
2. detect whether the Postgres volume is empty, stale, or incompatible
3. restore the published snapshot artifact when needed
4. run Alembic migrations or migration verification
5. write `.tmp_untracked/worktree.env` with `DATABASE_URL`, slot ports, and
   local artifact roots

Bootstrap will not:

- copy DuckDB files into the worktree
- copy Milvus files into the worktree
- rebuild catalog state from canonical source files during normal startup

### Storage boundaries

- `catalog` schema: seeded product rows, pgvector embeddings, image catalog
  metadata, and optional diversification state
- `app` schema: mutable runtime and user state
- `ops` schema: snapshot version and restore bookkeeping

### Snapshot artifact

The rewrite must define one explicit versioned Postgres snapshot artifact and a
matching manifest.

The artifact must be:

- created by top-level infra/data tooling
- buildable locally on demand
- buildable, validated, versioned, and published in CI
- restorable into a fresh local Postgres instance without rebuilding from
  canonical source files

### Canonical build inputs

- Product metadata: `data/parquet/products_canonical`
- Embedding source rows: `data/parquet/product_embeddings`
- Image catalog metadata: shared image catalog outputs under
  `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`

## Execution Order

1. `tal_maria_ikea-5p1.1`
   Rewrite the spec and plan to the corrected Postgres + pgvector architecture.
2. `tal_maria_ikea-5p1.2`
   Move snapshot and bootstrap data tooling out of `src/ikea_agent`.
3. `tal_maria_ikea-5p1.3`
   Add `pgvector` schema and indexing for product embeddings.
4. `tal_maria_ikea-5p1.10`
   Specify and implement snapshot creation locally and in CI.
5. `tal_maria_ikea-5p1.8`
   Restore versioned snapshots during normal bootstrap.
6. `tal_maria_ikea-5p1.4`
   Collapse retrieval into direct Postgres pgvector queries.
7. `tal_maria_ikea-5p1.5`
   Rework diversification in a Postgres-native form.
8. `tal_maria_ikea-5p1.6`
   Delete Milvus runtime, bootstrap, and configuration surfaces.
9. `tal_maria_ikea-5p1.7`
   Remove DuckDB compatibility from active codepaths and dependencies.
10. `tal_maria_ikea-5p1.9`
    Update validation, docs, and PR messaging for the corrected architecture.

## Snapshot Workflows To Implement Early

### Local snapshot creation

The rewrite must expose one explicit local command that:

1. creates an ephemeral Postgres builder
2. loads canonical catalog and image inputs
3. loads pgvector embeddings and any required derived neighbor state
4. validates restore into a fresh Postgres instance
5. writes the snapshot artifact plus manifest into the local snapshot cache

### CI snapshot creation

The rewrite must expose one CI workflow that:

1. rebuilds the artifact when relevant inputs change
2. validates restore and runtime compatibility
3. versions and publishes the artifact plus manifest

### Bootstrap restore

Normal worktree startup must consume the produced artifact, not rebuild from
source by default.

## Validation

Required before closing the rewrite:

- `make tidy`
- targeted backend tests while implementation is in flight
- `make ui-test-e2e-real-ui-smoke` after retrieval/image/runtime changes settle
- explicit acceptance notes covering the updated end states from
  `specs/docker-deps/target-state-spec.md`
