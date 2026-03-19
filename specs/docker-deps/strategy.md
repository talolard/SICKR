# Docker Dependency Strategy

Date: 2026-03-19

Source prompt: `specs/docker-deps/brain-dump.md`

## Executive Summary

The best fit for this repo is:

1. Move the writable runtime database from DuckDB to Postgres in Docker.
2. Keep Milvus as the vector store for now, but make it one shared Dockerized service for all worktrees.
3. Do not replace Milvus with Postgres in this phase; revisit that only after the Postgres migration is stable.
4. Move the image catalog metadata into Postgres as part of retiring DuckDB from the dev stack.
5. Keep product images out of application images and serve them from one shared read-only root at first, while designing the catalog so image storage can move later.
6. Treat Dev Containers as optional editor/tooling standardization on top of Compose, not as the primary solution to dependency isolation.

That direction solves the actual current pain:

- `scripts/worktree/bootstrap.sh` copies `data/ikea.duckdb` and `data/milvus_lite.db` into each worktree's `.tmp_untracked/runtime`.
- `docs/worktree_multi_agent_workflow.md` already documents DuckDB WAL and Milvus lock cleanup as a normal local recovery path.
- `src/ikea_agent/chat/runtime.py` still boots a DuckDB engine and a Milvus Lite client at startup.
- product images are already conceptually shared across worktrees through one root, but they are still served through backend routes instead of a dedicated static-serving layer.

The repo is already partially prepared for the Postgres move:

- SQLAlchemy and Alembic are in place.
- persistence models explicitly describe themselves as "DuckDB-first and Postgres-ready."
- the Milvus integration surface is small enough that switching from per-worktree file copies to one shared service is realistic.
- the remaining DuckDB dependency in the image-catalog path is small enough that it should be removed in the same initiative rather than preserved as a special case.

## Current State In This Repo

### Writable runtime state

- Default local runtime config uses `DUCKDB_PATH=data/ikea.duckdb` and `MILVUS_LITE_URI=data/milvus_lite.db` in `src/ikea_agent/config.py`.
- Worktree bootstrap overrides those to worktree-local copies in `.tmp_untracked/runtime` via `scripts/worktree/bootstrap.sh`.
- `Makefile` and `docs/worktree_multi_agent_workflow.md` explicitly encode that per-worktree isolation model.
- There is currently no checked-in `compose.yml`, `Dockerfile`, or `.devcontainer/` definition in the repo.

### DuckDB usage

- Active retrieval metadata and embedding snapshots live in DuckDB today, documented in `docs/data/index.md` and `docs/data/current_graph_data_access.md`.
- Runtime startup builds a DuckDB engine through `src/ikea_agent/shared/sqlalchemy_db.py` and `src/ikea_agent/chat/runtime.py`.
- Retrieval hydration SQL is already routed through SQLAlchemy in `src/ikea_agent/retrieval/catalog_repository.py`.
- Alembic is present, but the default migration URL still resolves to DuckDB in `migrations/env.py`.
- Retrieval schema creation is still partly outside Alembic in `src/ikea_agent/shared/bootstrap.py`, so the current schema story is not fully migration-driven yet.
- A large test surface still constructs temporary DuckDB databases directly through `create_duckdb_engine(...)`, so the migration is not only an ops change; it also needs test harness work.

### Milvus usage

- The active vector service is a very small wrapper in `src/ikea_agent/retrieval/service.py`.
- Runtime boot calls `ensure_collection()`, then hydrates Milvus from the embedding snapshot if the collection is empty in `src/ikea_agent/chat/runtime.py`.
- Ingest does the same from `src/ingest/hydrate_milvus.py`.
- The current deployment assumption is still worktree-local file state, not one shared service, because `scripts/worktree/bootstrap.sh` copies `data/milvus_lite.db` into each worktree runtime directory.

### Product image serving

- The shared image catalog root is already outside worktree-local runtime state via `ikea_image_catalog_root_dir` in `src/ikea_agent/config.py`.
- `src/ikea_agent/chat/product_images.py` builds an in-memory lookup from that shared root and maps product ids to file paths.
- `src/ikea_agent/chat_app/product_image_routes.py` serves bytes through FastAPI routes like `/static/product-images/{product_id}`.
- One subtle seam: parquet-backed image catalog loading still uses the `duckdb` Python package in `src/ikea_agent/chat/product_images.py`, so a Postgres migration does not automatically remove DuckDB from the developer dependency set.
- The image-serving recommendation should account for actual local size: `data/` is about `758M`, while `.tmp_untracked/ikea_image_catalog` is about `14G`.
- The current catalog source is sidecar-run output under `.tmp_untracked/ikea_image_catalog/runs/...`, which is useful for extraction, but not the right long-term runtime source if the goal is to make Postgres authoritative.

### SQLite

I did not find active SQLite usage in the current runtime path. The stateful stores in active use are DuckDB and Milvus Lite's local file.

## Repo-Specific Migration Seams

These are the places that should drive the implementation order.

### 1. Database configuration is still DuckDB-shaped

- `src/ikea_agent/config.py` exposes `DUCKDB_PATH`, not a generic `DATABASE_URL`.
- `src/ikea_agent/chat/runtime.py` always calls `create_duckdb_engine(...)`.
- `migrations/env.py` still defaults to a DuckDB URL builder.

Before Docker matters, the runtime needs one neutral database configuration path.

### 2. Retrieval bootstrapping is split between Alembic and ad hoc runtime schema creation

- durable persistence tables are in Alembic under `migrations/versions/`
- retrieval tables are still created at runtime in `src/ikea_agent/shared/bootstrap.py`

That split is manageable in DuckDB, but it is the wrong steady state for seeded Postgres volumes. Seed and migration logic should own schema creation deterministically.

### 3. Vector search is isolated enough to swap, but not fully abstracted yet

- the main Milvus-specific surface is `src/ikea_agent/retrieval/service.py`
- runtime wiring still stores a concrete `MilvusAccessService` on `ChatRuntime`
- ranking explanations and naming still mention Milvus directly in `src/ikea_agent/retrieval/catalog_repository.py`

This is a good migration seam, but a small protocol layer should exist before the backend changes.

### 4. Image serving is already shared, but image lookup is not yet static-server-friendly

- URLs are generated as backend-local paths in `src/ikea_agent/chat/product_images.py`
- FastAPI resolves `product_id` and optional ordinal dynamically in `src/ikea_agent/chat_app/product_image_routes.py`

That means a dedicated static server is viable, but only after image URL generation is decoupled from the current backend route assumptions.

### 5. The image catalog metadata is still outside the main runtime database

- runtime image lookup is built from sidecar output files, not from Postgres
- parquet-backed catalog reads still require the `duckdb` package
- the current lookup model assumes local filesystem paths are the source of truth

That is workable today, but it blocks the stated goal of fully retiring DuckDB and makes future image relocation harder than it needs to be.

### 1. Compose as the dependency boundary

Use Docker Compose to define local dependencies, not to containerize the app runtime immediately.

For each worktree:

- assign a unique Compose project name derived from slot or worktree slug, for example `COMPOSE_PROJECT_NAME=ikea-slot-07`
- run a per-worktree Postgres service
- optionally run other per-worktree services only when needed through Compose profiles

Recommended local commands:

- `make deps-up SLOT=7`
- `make deps-down SLOT=7`
- `make deps-reset SLOT=7`
- `make deps-reseed SLOT=7`

Compose should own service ports and volumes. The app should only consume connection settings written into `.tmp_untracked/worktree.env`.

### 2. Postgres first, with seed artifact plus migrations

Use Postgres as the first dependency to move into Docker.

The right boot pattern is:

1. Start Postgres with an empty per-worktree named volume.
2. If the volume is empty, restore a versioned seed artifact into it.
3. Run Alembic migrations to head.
4. Start the app against that database.

The seed artifact should not be "the running Postgres data directory baked into the runtime image."

The better split is:

- runtime image: thin Postgres image with required extensions installed
- seed artifact: a reproducible dump or restore input produced from the canonical dataset and schema
- migrations: Alembic, always run on startup or via an explicit migration step before app boot

For this repo, the seed artifact should be generated from the canonical catalog and embedding snapshot inputs, not by copying live per-worktree files around.

Postgres should also reflect the different change rates in this system.

At minimum, use two logical schemas:

- `catalog`: product catalog, embedding snapshot source data, and image catalog metadata
- `app`: evolving runtime and user-generated application state

I recommend a third lightweight operational schema if we want the cleanest separation:

- `ops`: seed metadata, refresh bookkeeping, and other operational tables that are not product data and not end-user app state

That split matters because the catalog side is effectively static for local development, while the app side changes as features evolve and as users interact with the system. We should leverage that asymmetry:

- catalog data can be seeded, versioned, and treated as read-mostly
- app data can remain migration-heavy and iteration-friendly
- local resets can cheaply recreate app state without having to rethink the whole catalog model

### 3. Keep Milvus, but make it one shared Dockerized service

This repo's current Milvus layer is narrow:

- `search()` returns candidate keys plus scores
- `upsert_rows()` replaces collection contents from the embedding snapshot
- empty-store hydration is already explicit

That is enough to support a cleaner operational change now:

- stop copying Milvus data into each worktree
- run one shared Milvus service for the whole machine
- point every worktree at that shared service

The important constraint is that a shared singleton Milvus should not be hydrated opportunistically by whichever worktree starts first. The seed and refresh story should move to one explicit global preparation step.

The practical architecture is:

- Postgres is per worktree
- Milvus is global and shared
- the app runtime still uses the existing Milvus integration surface
- the current metadata hydration and reranking flow remains unchanged

That keeps the storage split for now, but removes the most annoying Milvus-local copy and lock behavior without forcing a retrieval-backend rewrite in the same project.

### 4. Shared image serving should be one shared read-only dependency

Do not bake the IKEA image corpus into app containers.

Use one shared image root on the host, mounted read-only into exactly one static-serving process. Two viable steps:

1. Near term: keep FastAPI serving the files, but keep the shared root outside worktree-local runtime state.
2. Better steady state: generate a canonical static tree and serve it from one dedicated local static server container.

The current code does not yet expose canonical file paths directly; it resolves product ids dynamically from the image catalog. Because of that, a dedicated static server is easiest after adding a build step that materializes stable file paths per product id and ordinal.

### 5. Move the image catalog metadata into Postgres, but not the image bytes

If the goal is to fully give up DuckDB, the image catalog should move into Postgres as part of this initiative.

The right split is:

- Postgres stores image catalog metadata and serving metadata
- image bytes stay on disk or in an external object store
- runtime builds image URLs from Postgres-backed metadata, not from parquet scans

That gives you one authoritative runtime database without forcing binary image payloads into Postgres.

The catalog rows should be designed for eventual image relocation, so the schema should separate:

- product identity
- image identity and rank
- storage location
- public serving URL or URL template
- optional local fallback path for local development
- freshness and provenance metadata for future recrawls or catalog updates

In the Postgres layout above, this catalog belongs with the other mostly-static catalog data, not with mutable app state. That lets us treat product and image metadata as part of the same seeded read-mostly domain.

The backend work implied here is worth doing now:

- stop assuming backend-local `/static/product-images/...` is the only long-term URL shape
- make image base URL or serving strategy configurable
- move catalog lookup off `duckdb` parquet reads and onto typed Postgres queries
- keep local development able to serve from a shared read-only root while allowing future migration to object storage or another image host

## Direct Answers To The Questions

### Should each worktree get its own Postgres?

Yes.

That maps cleanly to the current slot-based worktree model and removes the single-writer and WAL sidecar problems that exist with DuckDB copies today. Per-worktree Postgres is also much more predictable than trying to share one mutable database across concurrent agents.

### Should the Postgres base be an image, a volume, or something else?

Use:

- a stable Postgres runtime image
- a per-worktree named data volume
- a separate seed artifact used only when the volume is empty

Do not treat a pre-populated runtime image as the primary data-distribution mechanism.

That approach keeps image rebuilds small, avoids storing mutable database state in image layers, and makes refresh logic explicit.

### Should startup run migrations?

Yes, but as a dedicated step.

Preferred order:

1. restore seed if volume is empty
2. run Alembic upgrade
3. start app

That gives you deterministic bootstrap and keeps migration failures visible.

### Should CI rebuild a "base image" when data or migrations change?

CI should rebuild the seed artifact when:

- canonical source data changes
- seed-generation code changes
- migrations change in ways that affect the seeded schema or data

CI does not need to rebuild the generic runtime Postgres image every time the data changes.

If you want one distributable local bootstrap asset, publish the seed artifact, not a mutable database image.

### Should Milvus also move to Docker?

Yes.

Given the current problems with copying Milvus state into each worktree, the best fit is one shared Dockerized Milvus service for the machine rather than one Milvus store per worktree.

That gives you:

- one canonical local vector index
- no per-worktree Milvus file copies
- no per-worktree Milvus lock cleanup path
- minimal code churn, because the runtime already talks to Milvus through a small wrapper

### If Milvus stays for a while, should it be one per worktree or shared?

Shared.

This is the deliberate exception to the per-worktree rule. Postgres should still be per worktree, but Milvus should become one global local dependency.

The reasons are straightforward:

- the indexed dataset is effectively shared across agents
- the current pain is caused by copying that state per worktree
- a singleton vector service is cheaper and simpler than multiplying it by slot
- the worktrees do not need isolated mutable Milvus state today

### Should Milvus data be pre-populated in the image or mounted as a volume?

Use:

- a thin runtime image or service definition
- one shared writable Docker volume
- one explicit global seed or refresh command

Do not rely on per-worktree copied files, and do not treat a pre-populated image as the primary data-distribution mechanism. The Milvus seed path should be explicit, global, and repeatable.

### Should the image catalog move to Postgres?

Yes.

If the initiative is meant to retire DuckDB rather than just shrink it, the image catalog metadata should move into Postgres too.

That does not mean storing image bytes in Postgres. It means storing the catalog and serving metadata there so runtime lookup is based on Postgres rows instead of parquet or JSONL sidecar files.

That is also the right preparation for later moving the images themselves somewhere else, because the storage location becomes data, not an implicit local-path convention baked into runtime code.

### How should shared product images be served across worktrees?

Best fit:

- keep one shared host-side image root
- mount it read-only
- expose it through one shared static-serving endpoint

Do not duplicate the image corpus per worktree.

In this repo specifically, the migration path should be:

1. keep the current shared root
2. make the image base URL configurable
3. later, add a materialized canonical static tree so a dedicated static server can replace the dynamic FastAPI route

### Would Dev Containers be better than plain Compose?

Not for the core problem you described.

Compose solves the dependency isolation problem. Dev Containers solve editor and toolchain consistency for humans using compatible IDE support.

For this repo:

- Compose should be the foundation
- Dev Containers are optional on top
- if added, they should reuse the same Compose services rather than replace them

Dev Containers become attractive if the team wants standardized Python, Node, `uv`, `pnpm`, browser, and CLI tooling inside one editor-managed environment. They do not replace the need for per-worktree dependency data isolation.

## Pros And Cons Of The Recommended Direction

### Pros

- eliminates DuckDB single-writer and WAL-copy pain
- aligns with the repo's existing SQLAlchemy and Alembic direction
- removes the need to copy mutable DB files into each worktree
- gives each agent an isolated, disposable dependency stack
- removes the need to copy Milvus state into each worktree
- keeps the current vector-search backend intact while fixing the operational model
- gives the image catalog one authoritative runtime source in Postgres
- makes full DuckDB removal from the dev runtime realistic
- leverages the fact that catalog data changes slowly while app state changes quickly
- keeps large static image data shared instead of duplicated

### Cons

- local bootstrap becomes more orchestration-heavy than copying two files
- Postgres seeding needs a real artifact-generation workflow
- moving retrieval SQL from DuckDB to Postgres will require deliberate query validation
- shared Milvus now needs explicit global seed/version management
- image-catalog serving and lookup need backend refactoring, not just infra changes
- a shared static file service requires either a canonical tree or a lightweight proxy layer

## Recommended Rollout Order

### Phase 0: document and isolate

- add Compose definitions and naming conventions for per-worktree dependency stacks
- introduce a `DATABASE_URL`-style config path alongside the current DuckDB-specific settings
- add a neutral engine-construction path so runtime and Alembic can target DuckDB or Postgres without branching all over the codebase
- add a small vector-store protocol so `ChatRuntime` stops depending on a concrete Milvus service
- keep current app runtime outside containers

### Phase 1: Postgres bootstrap

- create a Postgres image or service definition with required extensions
- define per-worktree named volumes
- add seed generation and restore commands
- switch Alembic and runtime boot to support Postgres cleanly
- move retrieval schema ownership out of `ensure_runtime_schema(...)` and into explicit migrations or seed/bootstrap steps

### Phase 2: data-path migration

- migrate retrieval metadata and persistence tables from DuckDB to Postgres
- validate retrieval queries and backfill routines against Postgres
- stop copying DuckDB files in worktree bootstrap
- update tests so the main database fixture story is no longer DuckDB-only

### Phase 3: Milvus centralization

- add one global Milvus Compose stack separate from per-worktree Postgres
- define one shared Milvus volume and one explicit global seed or refresh step
- change worktree bootstrap so it ensures global Milvus is running instead of copying `milvus_lite.db`
- point every worktree at the same Milvus service URI
- remove Milvus hydration-on-startup from normal worktree runtime boot, or gate it behind an explicit administrative path

### Phase 4: image catalog migration

- add Postgres-backed image catalog tables and migrations
- load existing image catalog metadata into Postgres from the current sidecar outputs
- switch runtime lookup from `duckdb` parquet reads to typed Postgres queries
- make image serving metadata explicit enough to support both local shared-root serving and future external image hosting
- remove the runtime `duckdb` dependency from the image-catalog path

### Phase 5: static image serving cleanup

- make image URLs configurable from a shared base URL
- materialize a canonical static image tree
- move image bytes off the app backend and onto one shared static-serving endpoint

### Phase 6: optional Dev Container support

- add a devcontainer that reuses Compose services
- only do this if the team wants editor/tooling standardization, not just dependency isolation

## Rough Spec

### Local dependency contract

- one Compose project per worktree for Postgres and other worktree-local services
- one global Compose project for Milvus
- one Postgres volume per worktree
- one shared Milvus volume for the machine
- no copied mutable DB files inside the repo
- one shared read-only image root outside those per-worktree volumes
- Postgres is the authoritative runtime source for retrieval, persistence, and image catalog metadata

### Postgres schema contract

- `catalog` schema stores seeded read-mostly product and image catalog data
- `app` schema stores evolving runtime and user-generated application state
- optional `ops` schema stores seed-version and refresh bookkeeping if we want to keep operational metadata out of both main domains

This split is intentional, not cosmetic. The catalog side has near-zero development churn compared with the app side, and the storage design should reflect that.

### Seed contract

- canonical inputs live in source-controlled data or generated artifacts
- a reproducible seed build produces a restore artifact
- fresh local volumes restore from that artifact
- Alembic then upgrades to head
- global Milvus is seeded or refreshed by one explicit global command, not implicitly by arbitrary worktree startup
- image catalog metadata is loaded into Postgres as part of the same reproducible seed or refresh flow

### App contract

- runtime config should accept a real database URL
- vector search should be behind a protocol or service interface, not hard-wired to Milvus types in the runtime container object
- image URLs should be driven by config and catalog metadata, not assumed to be backend-local static routes forever

## Early Decisions To Make

### Seed format

Pick one of these early and keep it stable:

- preferred: a logical Postgres dump restored into empty volumes
- acceptable: a typed import pipeline from parquet or CSV plus an explicit loader

The main requirement is reproducibility from canonical inputs, not cleverness.

### Empty-volume detection

Do not infer initialization state from "some tables exist."

Use one explicit seed marker, for example:

- `alembic_version` present and current
- plus one `app.seed_metadata` table with the expected seed version

That will make refresh, reset, and debugging much easier than implicit heuristics.

### Image hosting boundary

Do not let the static-image decision become bigger than the database-isolation decision.

The hard problem in this repo is mutable database state across worktrees. The current FastAPI image route is acceptable until it causes real pain.

### Image catalog schema

Design the Postgres-backed image catalog so it survives a later storage move.

That means catalog rows should model at least:

- canonical product key or raw product id linkage
- ordinal or ranking metadata
- source provenance
- serving URL or URL template
- storage backend kind, for example `local_shared_root` or `remote_object_store`
- local filesystem path only as one optional storage-specific field, not the universal contract
- updated timestamps and refresh versioning

## External References Used

- Docker Compose project naming and isolation:
  - <https://docs.docker.com/compose/how-tos/project-name/>
- Docker Compose profiles:
  - <https://docs.docker.com/compose/how-tos/profiles/>
- Docker volumes and bind mounts:
  - <https://docs.docker.com/engine/storage/volumes/>
  - <https://docs.docker.com/engine/storage/bind-mounts/>
- Docker Official Image guidance for Postgres initialization:
  - <https://hub.docker.com/_/postgres>
- PostgreSQL dump and restore:
  - <https://www.postgresql.org/docs/current/app-pgdump.html>
  - <https://www.postgresql.org/docs/current/app-pgrestore.html>
- Milvus Lite and Milvus standalone docs:
  - <https://milvus.io/docs/milvus_lite.md>
  - <https://milvus.io/docs/install_standalone-docker-compose.md>
- VS Code Dev Containers and the devcontainer spec:
  - <https://code.visualstudio.com/docs/devcontainers/containers>
  - <https://code.visualstudio.com/docs/devcontainers/create-dev-container>
  - <https://containers.dev/implementors/json_reference/>

Those sources support the main operational guidance here:

- use Compose project names for isolated stacks
- use named volumes for stateful containers
- seed Postgres on empty volumes instead of baking mutable database state into runtime images
- keep shared singleton services outside per-worktree stacks when the data is intentionally global
- treat Dev Containers as additive to Compose
