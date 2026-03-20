# Docker Dependency Strategy

Date: 2026-03-19

Source prompt: `specs/docker-deps/brain-dump.md`

## Executive Summary

The previous version of this strategy preserved Milvus and treated Postgres as a
catalog store plus app database. That was the wrong cut for this repo.

The corrected strategy is:

1. Move the active local search backend fully into Postgres.
2. Use `pgvector` for vector retrieval inside Postgres.
3. Remove Milvus from runtime, bootstrap, config, docs, and local dependency
   orchestration.
4. Remove DuckDB from the active application, bootstrap, and dependency path.
5. Make snapshot creation a first-class artifact workflow, implemented early.
6. Make normal bootstrap restore a versioned Postgres snapshot instead of
   rebuilding catalog state from canonical source files.
7. Keep image bytes outside Postgres, but store image catalog metadata in the
   seeded `catalog` schema.

This is simpler than the earlier split design:

- one stateful search backend instead of two
- one seed/restore lifecycle instead of Postgres plus Milvus preparation
- one query system for vector ranking and structured filtering
- one local dependency to bootstrap for search data access

## Why The Earlier Plan Was Wrong

The repo's current search path already has a strong relational center:

- vector search returns candidate keys and scores
- product hydration, filtering, and result shaping happen afterward in the
  relational store
- image metadata and other catalog concerns are also relational

That means retaining Milvus in this migration would keep a second stateful
dependency without meaningfully simplifying the application model. It would add:

- a second persistent lifecycle
- a second seed and refresh contract
- more bootstrap complexity
- more operator surface
- more runtime wiring to remove later

If Postgres already owns the catalog and the search path still needs relational
filtering and hydration, the clean design is to let Postgres own vectors too.

## Recommended Architecture

### 1. Postgres is the only local search dependency

Each worktree gets one local Postgres service and one named volume.

That Postgres instance owns:

- seeded product catalog metadata
- seeded image catalog metadata
- seeded embeddings
- optional precomputed neighbor or diversification state
- mutable app tables
- operational snapshot metadata

Local runtime search should require only:

- Postgres
- the shared image root or whichever image-serving strategy is configured

Milvus is not part of the target system.

### 2. Postgres performs vector retrieval through `pgvector`

Embeddings are not just stored in Postgres as arrays for later export.
They are queried in Postgres directly.

The target shape is:

- `catalog.product_embeddings.embedding_vector` is a `pgvector` column
- the database has the required `pgvector` extension installed
- the embedding table has the vector index appropriate for the chosen distance
  metric
- retrieval expresses vector distance through SQLAlchemy constructs instead of
  handwritten SQL text blocks

This is the missing piece that turns Postgres from a staging store into the
actual search backend.

### 3. Retrieval collapses into one repository query layer

The target search flow is:

1. embed the query text
2. execute one Postgres repository query
3. return hydrated `RetrievalResult` rows

That repository layer should:

- join seeded product metadata and embeddings
- apply structured filters
- rank by vector similarity
- optionally use a candidate pool for reranking or alternate sorts
- return fully hydrated rows directly

The repo should not keep the old split boundary of:

- search in one backend
- hydrate and filter in another backend

That split is exactly the complexity this rewrite is meant to remove.

### 4. The active retrieval path should use SQLAlchemy query construction

For the corrected architecture, the active retrieval path should be written with
SQLAlchemy query construction rather than handwritten SQL text blocks.

That applies especially to:

- the main search query
- product lookup by key
- any remaining diversification query
- restore-time or seed-time Postgres access that remains part of active repo
  tooling

Small typed SQL may still be acceptable in one-off infra scripts, but the
runtime search path should not remain a large SQL-text surface assembled around
handwritten statement strings.

## Snapshot Strategy

Snapshot creation was missing from the earlier spec. It is a first-class part of
the corrected design and must be implemented early.

### Snapshot artifact contract

The repo should define one explicit Postgres snapshot artifact format.

Recommended shape:

- a logical Postgres dump created from a prepared Postgres instance
- produced with a stable command such as `pg_dump --format=custom`
- accompanied by a machine-readable manifest

The artifact contents must already include:

- `catalog.products_canonical`
- `catalog.product_embeddings` with `pgvector` data
- `catalog.product_images`
- any required precomputed neighbor or diversification structure
- migrated `app` tables that must exist in fresh local instances
- `ops.seed_state` or equivalent snapshot metadata

The manifest should include at least:

- snapshot version
- schema migration head used when building it
- canonical data fingerprints used as inputs
- snapshot builder version
- build timestamp
- distance metric and embedding model metadata where relevant

### Local snapshot creation

Developers need one explicit local command that builds or refreshes the
snapshot.

Recommended operator contract:

- build an ephemeral Postgres instance with the required extensions installed
- run migrations
- load canonical catalog and image data
- load embeddings into `pgvector`
- build any required precomputed neighbor state
- validate restore into a separate fresh Postgres instance
- write the snapshot artifact plus manifest into a top-level local cache path

Suggested local output root:

- `CANONICAL_ROOT/.tmp_untracked/docker-deps/snapshots/<version>/`

The important point is not the exact path. The important point is that snapshot
creation is:

- explicit
- reproducible
- local when needed
- outside `src/ikea_agent/`

### CI snapshot creation and publication

CI must also build the same artifact.

The CI workflow should trigger when relevant inputs change, including:

- migrations
- canonical catalog sources
- image catalog sources or import logic
- snapshot builder scripts
- search-schema shaping changes that alter snapshot contents

The CI workflow should:

1. build a fresh Postgres snapshot from canonical inputs
2. validate that the artifact restores into a fresh Postgres instance
3. validate that the restored database supports runtime boot and at least one
   search smoke path
4. publish the artifact and manifest under a stable version identity

Bootstrap should consume the published artifact contract, not guess how to
rebuild data itself.

### Snapshot restore

Normal bootstrap should:

1. start slot-local Postgres
2. detect whether the volume is empty or stale
3. restore the published snapshot into that volume when needed
4. run migrations or migration verification
5. write worktree environment

Normal bootstrap must not rebuild the search database from canonical source
files by default.

Rebuild-from-source remains a maintenance workflow, not the common path.

## Schema Boundaries

Use these schemas:

- `catalog`: seeded read-mostly product, embedding, image, and optional
  diversification data
- `app`: mutable runtime and user state
- `ops`: snapshot metadata, restore bookkeeping, and other operational tables

This split is still useful in the corrected architecture because:

- `catalog` is versioned and seeded
- `app` is iterative and migration-heavy
- `ops` is operational rather than product-facing

## Diversification Strategy

The previous plan carried forward `product_embedding_neighbors` plus a Python
cosine fallback from the Milvus-era world.

The chosen strategy is direct pgvector similarity over the already-small
candidate set selected for rerank/MMR.

That means:

- active runtime reads pairwise candidate similarities directly from
  `catalog.product_embeddings`
- the HNSW cosine index on `catalog.product_embeddings.embedding_vector` remains
  the primary retrieval index
- precomputed neighbor rows are optional legacy data only and are not required
  for the active path

The active system must not remain a half-runtime, half-fallback hybrid.

## Image Serving Strategy

Image bytes still do not belong in Postgres.

The target split is:

- Postgres stores image catalog metadata and serving metadata
- image bytes remain in a shared local root or future external storage
- runtime builds image URLs from Postgres-backed metadata

This preserves current local serving while keeping the schema ready for later
storage relocation.

FastAPI may remain the initial image-serving boundary, but the image contract
should not assume that backend-local proxy routes are the only future shape.

## Compose And Bootstrap Boundary

Compose should be the dependency boundary for local infrastructure.

For the corrected architecture:

- one slot-scoped Postgres Compose stack is required
- no shared Milvus Compose stack remains
- optional image-serving infrastructure can be layered separately if needed

Recommended local commands:

- `make deps-up SLOT=7`
- `make deps-down SLOT=7`
- `make deps-reset SLOT=7`
- `make deps-restore SLOT=7`
- `make deps-snapshot-build`

Exact command names can evolve, but the split should stay clear:

- snapshot build is explicit infra/data work
- snapshot restore is normal bootstrap work

## Direct Answers To The Brain-Dump Questions

### Should each worktree get its own Postgres?

Yes.

That preserves mutable state isolation and eliminates DuckDB's one-writer and
WAL recovery problems.

### Should the Postgres base be an image, a volume, or something else?

Use:

- a stable Postgres runtime image with required extensions installed
- one per-worktree named data volume
- one separate versioned snapshot artifact restored into empty or stale volumes

Do not use a prepopulated mutable runtime image as the main data-distribution
mechanism.

### Should startup run migrations?

Yes, as a dedicated step after restore.

Preferred order:

1. restore snapshot when needed
2. run migrations or migration verification
3. boot the app

### How should snapshot creation work locally?

One explicit top-level command should build the artifact from canonical inputs,
validate restore, and place the resulting snapshot plus manifest in the local
snapshot cache.

It should not live under `src/ikea_agent/`.

### How should snapshot creation work in CI?

CI should rebuild, validate, version, and publish the same artifact when
relevant inputs change.

### What about Dev Containers?

Treat Dev Containers as optional tooling standardization on top of the corrected
dependency model, not as the primary solution.

The dependency problem here is stateful local search data and predictable
bootstrap. Dev Containers do not replace the need for:

- Postgres snapshot creation
- Postgres snapshot restore
- clear bootstrap contracts

## Implementation Order

The order that best fits this repo is:

1. rewrite the specs and plan to the corrected Postgres-only architecture
2. move snapshot and bootstrap data tooling out of `src/ikea_agent`
3. add `pgvector` schema and indexing
4. implement snapshot creation locally and in CI
5. implement snapshot restore during normal bootstrap
6. collapse retrieval into direct Postgres queries
7. rework diversification in Postgres-native form
8. remove Milvus from runtime/bootstrap/config/docs
9. remove DuckDB from active runtime/bootstrap/dependency paths
10. finish docs, smoke coverage, and final validation

Snapshot creation is early because restore and bootstrap cannot be real until
there is a real artifact to restore.
