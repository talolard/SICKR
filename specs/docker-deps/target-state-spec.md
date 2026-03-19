# Dockerized Local Dependency Target State

Date: 2026-03-19

Source inputs:

- `specs/docker-deps/brain-dump.md`
- `specs/docker-deps/strategy.md`

## Goal

Replace the current per-worktree copied DuckDB and Milvus file model with a Dockerized local dependency model that:

- uses Postgres as the single runtime database
- uses one shared Milvus service for all local worktrees
- seeds both systems so startup does not rebuild the world each time
- moves product and image catalog metadata into Postgres
- fully removes DuckDB from the active local runtime path

The target experience is:

1. A worktree bootstrap ensures the shared Milvus service exists and is healthy.
2. The same bootstrap creates or starts a worktree-local Postgres.
3. Postgres is ready with seeded catalog and image metadata plus migrated app tables.
4. Milvus is ready with the shared vector index already present in a persistent volume.
5. Any agent in any worktree can use Postgres, Milvus, and the image service without copying stateful files into the repo.

## Non-Goals

- Replacing Milvus with Postgres vector search in this initiative.
- Storing image bytes in Postgres.
- Fully containerizing the app runtime or developer shell as the first milestone.

## Target System

## Dependency topology

The local system will have two dependency scopes:

- one global dependency scope for Milvus
- one per-worktree dependency scope for Postgres

The global scope exists because the vector index is intentionally shared across worktrees.
The per-worktree scope exists because app development needs isolated mutable database state.

## Postgres

Each worktree will have its own Postgres service and its own named volume.

Postgres becomes the authoritative runtime database for:

- product catalog metadata
- image catalog metadata
- app state
- seed and refresh bookkeeping

Recommended schema layout:

- `catalog`: seeded read-mostly product and image catalog data
- `app`: evolving runtime and user-generated application state
- `ops`: optional but recommended operational metadata such as seed versions and refresh status

This split is intentional:

- `catalog` changes slowly and should be treated as a versioned seeded domain
- `app` changes quickly and should remain migration-friendly
- `ops` keeps operational tables out of both product and app domains

## Milvus

There will be exactly one local Milvus service for the machine.

That Milvus service will:

- run in a fixed global Compose project
- use a persistent named volume
- expose one stable URI used by all worktrees
- be seeded or refreshed explicitly, not implicitly by whichever worktree starts first

Milvus remains the vector store in this initiative.

## Image storage and serving

Image catalog metadata moves into Postgres.
Image bytes do not.

Image bytes will initially remain in one shared read-only local image root. The system will be designed so that image storage can later move elsewhere without another catalog redesign.

Assume that later image storage could be: S3 or a CDN.
The catalog contract will store enough information to support both:

- local shared-root serving
- future external or object-store-backed serving

## Bootstrap behavior

The worktree bootstrap becomes an orchestration step, not a file-copy step.

Bootstrap must:

1. ensure global Milvus is running
2. fail fast if Milvus cannot be started or reached
3. create or start the worktree-local Postgres
4. ensure the worktree-local Postgres seed and migrations are current
5. write environment for the worktree to consume those services

Bootstrap must not:

- copy DuckDB files into the worktree
- copy Milvus files into the worktree
- opportunistically reseed the shared Milvus just because one worktree started

## Seeds and persistent volumes

Both Postgres and Milvus will be backed by persistent Docker volumes.

Postgres volume responsibilities:

- store the worktree-local database files
- contain seeded `catalog` and image catalog data
- contain migrated `app` tables

Milvus volume responsibilities:

- store the global vector index
- survive service restarts
- avoid rehydrating the entire index on each startup

Seeds are explicit artifacts or import flows. Seeds are not equivalent to "whatever files happened to exist locally before startup."

## Testable End States

The initiative is complete when all of the following are true.

1. `scripts/worktree/bootstrap.sh` checks whether the global Milvus service is reachable, attempts to start it if it is not, and fails with a clear error if it still cannot reach it.
2. `scripts/worktree/bootstrap.sh` creates or starts a worktree-local Postgres service and fails clearly if that Postgres cannot be made healthy.
3. The bootstrap flow writes worktree-local environment that points to worktree-local Postgres and shared global Milvus, with no worktree-local `milvus_lite.db` or DuckDB file copies.
4. Postgres has at least the `catalog` and `app` schemas, and optionally `ops`, with those roles documented and enforced by code and migrations.
5. The `catalog` schema contains seeded product catalog data and seeded image catalog metadata.
6. The `app` schema contains migrated runtime tables for active application state.
7. The shared Milvus service has a persistent seeded index in its Docker volume and does not require full rehydration on each startup.
8. Both Postgres and Milvus have explicit seed version or refresh metadata, so the system can tell whether they are current.
9. Resetting one worktree's Postgres does not affect another worktree's Postgres or the shared Milvus service.
10. Stopping and restarting Docker does not require rebuilding the catalog database or Milvus index from scratch if the volumes are still present.
11. Any agent in any worktree can perform vector retrieval through the shared Milvus service successfully.
12. Any agent in any worktree can resolve product images successfully through the configured image service path.
13. Runtime image lookup uses Postgres-backed image catalog queries rather than DuckDB parquet reads.
14. The active local runtime path no longer depends on DuckDB files or DuckDB query execution.
15. The image catalog schema can represent both the current shared local image root and a future non-local storage backend without another contract rewrite.

## Functional Spec

## Service layout

The repo will define:

- one global Compose stack for Milvus
- one per-worktree Compose stack for Postgres

Milvus will use a fixed project name, for example `ikea-global`.
Postgres will use a slot or worktree-specific project name, for example `ikea-slot-07`.

## Postgres data model

Postgres will contain:

- a seeded read-mostly `catalog` schema
- a mutable `app` schema
- optional `ops` schema for operational metadata

`catalog` will include at least:

- product rows
- embedding snapshot source rows needed to seed or refresh Milvus
- image catalog rows

`app` will include at least:

- current runtime persistence tables already managed by Alembic
- any future mutable per-thread, per-run, or per-user tables

`ops` will include, if adopted:

- Postgres seed version metadata
- image catalog refresh metadata
- any operational timestamps or bookkeeping needed for refresh logic

## Image catalog contract

The Postgres-backed image catalog must store enough metadata to drive runtime lookup and future image relocation.

At minimum, each cataloged image needs:

- product linkage
- image identifier
- rank or ordinal
- provenance
- storage backend kind
- storage locator
- public serving URL or URL template when applicable
- optional local filesystem path for local shared-root serving
- timestamps and refresh version metadata

The universal contract must not assume a local filesystem path is always present.

## Milvus contract

Milvus remains the active vector store.

The system must provide:

- one stable Milvus URI for all worktrees
- one explicit global prepare or refresh path
- one persistent volume containing the shared index

Normal app startup must not be the place where shared Milvus is rebuilt from scratch.

## Image service contract

There will be one image-serving path usable by all worktrees.

The initial implementation may keep FastAPI serving images from a shared read-only root.
The important requirement is that:

- the serving strategy is configurable
- the lookup metadata lives in Postgres
- the contract does not prevent later migration to a dedicated static service or remote object store

## Units Of Work

## Epic 1: Compose And Bootstrap Orchestration

Goal:
Replace file-copy bootstrap with dependency orchestration.

Tasks:

- Define a global Compose stack for Milvus.
- Define a per-worktree Compose stack for Postgres.
- Add health checks and readiness waits for both services.
- Update `scripts/worktree/bootstrap.sh` to ensure global Milvus, then ensure local Postgres.
- Remove worktree-local copying of DuckDB and Milvus files from bootstrap.
- Write worktree environment variables for shared Milvus and local Postgres.
- Add `make` targets for dependency up, down, reset, reseed, and diagnostics.

## Epic 2: Postgres Database Foundation

Goal:
Make Postgres the single active runtime database.

Tasks:

- Introduce a real `DATABASE_URL`-style configuration path.
- Add Postgres engine creation and switch runtime wiring away from DuckDB-only engine helpers.
- Update Alembic configuration to support Postgres as the default local path.
- Move retrieval schema ownership out of runtime bootstrap and into migrations or explicit seed/bootstrap steps.
- Define and document the `catalog`, `app`, and optional `ops` schema boundaries.
- Add tests that exercise Postgres-backed runtime setup.

## Epic 3: Seed Model And Operational Metadata

Goal:
Make both databases reproducibly seedable and inspectable.

Tasks:

- Define the Postgres seed artifact or import flow.
- Define the Milvus seed or refresh flow.
- Add explicit seed-version metadata for Postgres.
- Add explicit seed-version or refresh metadata for Milvus.
- Add commands or one-shot services for seed, reseed, and refresh operations.
- Define failure behavior when a seed is missing, stale, or incompatible.

## Epic 4: Milvus Centralization

Goal:
Keep Milvus, but stop treating it as a per-worktree file.

Tasks:

- Run Milvus in a single global local dependency stack.
- Give Milvus a persistent shared volume.
- Change app config to use a shared Milvus URI.
- Remove normal worktree startup behavior that hydrates Milvus if empty.
- Introduce an explicit administrative prepare or refresh path for the shared Milvus index.
- Validate concurrent access from multiple worktrees.

## Epic 5: Image Catalog Migration To Postgres

Goal:
Retire DuckDB from the image lookup path and make Postgres authoritative.

Tasks:

- Design Postgres image catalog tables under the `catalog` schema.
- Add migrations for those tables.
- Build a loader that imports current sidecar catalog outputs into Postgres.
- Replace runtime DuckDB/parquet image catalog queries with typed Postgres queries.
- Add refresh metadata so future image catalog updates are traceable.
- Remove the runtime need for DuckDB in the image-catalog path.

## Epic 6: Image Serving Contract Cleanup

Goal:
Keep image serving working now while enabling a later move of the underlying image storage.

Tasks:

- Make image base URL or image serving strategy configurable.
- Ensure agents resolve images through catalog metadata instead of implicit backend-local conventions.
- Keep local shared-root serving working for development.
- Define the storage backend abstraction in the catalog schema, including local and future remote backends.
- Optionally introduce one dedicated image service if the current backend route becomes a bottleneck or coupling problem.

## Epic 7: Validation, Docs, And Rollout

Goal:
Make the new model operable and trustworthy.

Tasks:

- Update local workflow docs and worktree bootstrap docs.
- Add smoke tests covering bootstrap, Postgres readiness, Milvus readiness, and image resolution.
- Add checks proving no DuckDB or per-worktree Milvus copies are required in the active runtime path.
- Add reset and recovery runbooks for local failures.
- Define the final cutover point where DuckDB is no longer part of supported local development.

## Suggested Execution Order

1. Epic 1: Compose And Bootstrap Orchestration
2. Epic 2: Postgres Database Foundation
3. Epic 3: Seed Model And Operational Metadata
4. Epic 4: Milvus Centralization
5. Epic 5: Image Catalog Migration To Postgres
6. Epic 6: Image Serving Contract Cleanup
7. Epic 7: Validation, Docs, And Rollout

## Exit Criteria

This spec is satisfied when:

- bootstrap no longer copies DuckDB or Milvus files into worktrees
- Postgres is the only runtime database
- Milvus is one shared healthy local service with a persistent seeded volume
- product and image catalog metadata live in Postgres
- image bytes remain resolvable locally and the catalog can later point elsewhere
- all active worktrees can use the same global Milvus and their own local Postgres concurrently
