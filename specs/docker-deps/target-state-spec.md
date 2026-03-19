# Dockerized Local Dependency Target State

Date: 2026-03-19

Source inputs:

- `specs/docker-deps/brain-dump.md`
- `specs/docker-deps/strategy.md`

## Goal

Replace the current per-worktree copied DuckDB and Milvus file model with a
Dockerized local dependency model that:

- uses Postgres as the only active local search database
- uses `pgvector` for vector retrieval inside Postgres
- restores a versioned Postgres snapshot during normal bootstrap
- makes snapshot creation explicit for both local development and CI
- moves product and image catalog metadata into Postgres
- fully removes Milvus and DuckDB from the active local runtime path

The target experience is:

1. A worktree bootstrap starts or reaches slot-local Postgres.
2. Bootstrap restores the published Postgres snapshot when the slot volume is
   empty, stale, or incompatible.
3. Postgres is ready with seeded catalog data, pgvector embeddings, image
   metadata, and migrated app tables.
4. Any agent in any worktree can perform retrieval and image resolution without
   copying stateful database files into the repo.

## Non-Goals

- Storing image bytes in Postgres.
- Fully containerizing the app runtime or developer shell as the first
  milestone.
- Preserving Milvus as an active runtime dependency.

## Target System

### Dependency topology

The local system has one required stateful dependency scope for search data:

- one per-worktree Postgres service and volume

Optional image-serving infrastructure may exist, but search data access itself
must require only Postgres.

### Postgres

Each worktree has its own Postgres service and its own named volume.

Postgres becomes the authoritative runtime database for:

- product catalog metadata
- vector retrieval
- image catalog metadata
- app state
- snapshot and restore bookkeeping

Recommended schema layout:

- `catalog`: seeded read-mostly product, embedding, image, and optional
  diversification state
- `app`: evolving runtime and user-generated application state
- `ops`: operational metadata such as snapshot version and restore status

### Vector search

Vector retrieval is Postgres-native.

Requirements:

- `catalog.product_embeddings.embedding_vector` uses `pgvector`
- the required extension is installed through migrations or deterministic setup
- the embedding table has the vector index required by the chosen distance
  metric
- runtime query construction expresses vector distance through SQLAlchemy, not a
  separate vector service

### Image storage and serving

Image catalog metadata lives in Postgres.
Image bytes do not.

Image bytes initially remain in one shared read-only local image root.
The metadata contract must support both:

- current local shared-root serving
- future external or object-store-backed serving

### Snapshot artifact

The system defines one explicit versioned Postgres snapshot artifact.

The snapshot contents must include:

- seeded `catalog` tables for products, embeddings, and images
- any required precomputed diversification structure
- migrated runtime tables required in a fresh local database
- `ops` metadata sufficient to identify the snapshot version and build inputs

The snapshot is an artifact, not "whatever happened to exist in a previous local
volume."

## Snapshot Creation

Snapshot creation is first-class and must be implemented early.

### Local snapshot creation

There must be one explicit local command that:

1. creates an ephemeral Postgres builder instance
2. installs extensions and applies migrations
3. loads canonical catalog and image inputs
4. loads pgvector embeddings
5. builds any required neighbor or diversification state
6. validates restore into a fresh Postgres instance
7. writes the snapshot artifact and manifest into the local snapshot cache

The snapshot builder must live in top-level infra/data tooling, not under
`src/ikea_agent/`.

### CI snapshot creation

There must be one CI path that:

1. rebuilds the snapshot artifact when relevant inputs change
2. validates restore into a fresh Postgres instance
3. validates runtime compatibility for the restored database
4. versions and publishes the snapshot artifact plus manifest

Relevant inputs include at least:

- migrations
- canonical catalog sources
- image catalog import logic
- snapshot builder logic
- schema changes that alter snapshot contents

### Snapshot metadata

The manifest or equivalent metadata must include:

- snapshot version
- migration head
- input fingerprints
- builder version
- build timestamp
- any embedding-model or distance-metric metadata required for compatibility

## Bootstrap Behavior

The worktree bootstrap becomes an orchestration and restore step, not a
file-copy or rebuild step.

Bootstrap must:

1. create or start the worktree-local Postgres
2. detect whether the local Postgres volume is empty, stale, or incompatible
3. restore the published snapshot when needed
4. run migrations or migration verification
5. write environment for the worktree to consume that Postgres instance

Bootstrap must not:

- copy DuckDB files into the worktree
- copy Milvus files into the worktree
- rebuild the catalog database from canonical source files during normal startup

## Testable End States

The initiative is complete when all of the following are true.

1. `scripts/worktree/bootstrap.sh` creates or starts a worktree-local Postgres
   service and fails clearly if that Postgres cannot be made healthy.
2. Bootstrap writes worktree-local environment that points to slot-local
   Postgres, with no worktree-local DuckDB or Milvus file copies.
3. Postgres has `catalog`, `app`, and `ops` schema boundaries documented and
   enforced by code and migrations.
4. The `catalog` schema contains seeded product catalog data, pgvector
   embeddings, image catalog metadata, and any required diversification state.
5. The `app` schema contains migrated runtime tables for active application
   state.
6. Snapshot creation is implemented as an explicit local workflow with one
   documented developer command.
7. Snapshot creation is implemented as an explicit CI workflow that rebuilds,
   validates, versions, and publishes the artifact when relevant inputs change.
8. A fresh Postgres volume can be restored from the published snapshot without
   rebuilding from canonical source files.
9. Snapshot metadata is explicit enough for bootstrap and runtime to determine
   which snapshot version is present.
10. Resetting one worktree's Postgres does not affect another worktree's
   Postgres.
11. Stopping and restarting Docker does not require rebuilding the catalog
   database if the slot volume or restorable snapshot is still current.
12. Any agent in any worktree can perform vector retrieval through Postgres
   successfully.
13. Any agent in any worktree can resolve product images successfully through
   the configured image service path.
14. Runtime image lookup uses Postgres-backed image catalog queries rather than
   DuckDB parquet reads.
15. The active local runtime path no longer depends on Milvus or DuckDB files,
   services, or query execution.
16. The active retrieval implementation uses SQLAlchemy query construction
   instead of the old split Milvus-plus-hydration model.
17. The image catalog schema can represent both the current shared local image
   root and a future non-local storage backend without another contract rewrite.

## Functional Spec

### Service layout

The repo defines:

- one per-worktree Compose stack for Postgres
- optional image-serving support when needed

It does not define an active shared Milvus runtime dependency.

### Postgres data model

Postgres contains:

- a seeded read-mostly `catalog` schema
- a mutable `app` schema
- an `ops` schema for operational metadata

`catalog` includes at least:

- product rows
- pgvector-backed embedding rows
- image catalog rows
- optional persisted diversification state

`app` includes at least:

- current runtime persistence tables already managed by Alembic
- future mutable per-thread, per-run, or per-user tables

`ops` includes at least:

- snapshot version metadata
- restore bookkeeping
- compatibility markers needed for bootstrap decisions

### Retrieval contract

The main search path is:

1. embed query text
2. execute one Postgres repository query
3. return hydrated retrieval results

The active retrieval path must:

- apply structured filters in Postgres
- rank by pgvector similarity in Postgres
- avoid the old "candidate keys first, relational hydration later" split

### Diversification contract

Diversification, if retained, must be Postgres-native.

The repo may choose either:

- on-the-fly pgvector neighbor queries
- or one explicit persisted neighbor structure refreshed on demand

If persisted, that structure is part of the snapshot or explicit maintenance
refresh model.

### Image catalog contract

The Postgres-backed image catalog must store enough metadata to drive runtime
lookup and future image relocation.

At minimum, each cataloged image needs:

- product linkage
- image identifier
- rank or ordinal
- provenance
- storage backend kind
- storage locator
- public serving URL or URL template when applicable
- optional local filesystem path for local shared-root serving
- timestamps and refresh or snapshot version metadata

The universal contract must not assume a local filesystem path is always
present.

## Units Of Work

### Epic 1: Rewrite spec and plan

Goal:
Replace the earlier Milvus-preserving architecture with the corrected
Postgres-only contract.

### Epic 2: Move snapshot and bootstrap tooling out of the application package

Goal:
Ensure snapshot build and restore logic lives in top-level infra/data tooling,
not under `src/ikea_agent/`.

### Epic 3: Add pgvector schema and indexing

Goal:
Make Postgres the actual vector search backend.

### Epic 4: Implement snapshot creation locally and in CI

Goal:
Create the versioned Postgres artifact before restore/bootstrap work depends on
it.

### Epic 5: Implement snapshot restore during bootstrap

Goal:
Make normal startup restore the published artifact instead of rebuilding from
source.

### Epic 6: Collapse retrieval into direct Postgres queries

Goal:
Remove the split Milvus-plus-relational retrieval architecture.

### Epic 7: Remove Milvus and DuckDB from active runtime paths

Goal:
Finish deleting the old dependency surfaces after the Postgres-native search
path exists.

### Epic 8: Validation and docs

Goal:
Bring tests, smoke coverage, docs, and PR messaging into sync with the corrected
single-database architecture.
