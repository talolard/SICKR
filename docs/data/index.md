# Data Model and Storage

## Active Runtime Stores

### Postgres (`DATABASE_URL`)

Active runtime uses Postgres for:
- `catalog.products_canonical` (seeded catalog metadata)
- `catalog.product_embeddings` (seeded embedding snapshots used directly by pgvector retrieval)
- `catalog.product_embedding_neighbors` (optional legacy precomputed neighbor rows; active MMR no longer depends on them)
- `catalog.product_images` (seeded image metadata for runtime image lookup)
- `app.*` conversation and analysis tables managed by existing runtime migrations
- `ops.seed_state` (observable seed versions and refresh metadata)
  - includes `postgres_snapshot` rows after a versioned snapshot artifact is built

## Migrations

- Runtime schema migrations use Alembic + SQLAlchemy.
- See [Runtime DB Migrations](migrations.md) for commands and environment overrides.
- Snapshot artifact build/validation details live in [Postgres Snapshot Builds](postgres_snapshots.md).
- Local product-image serving and payload enrichment are documented in [Local Product Images](product_images.md).

## Data Lifecycle

1. `scripts/worktree/deps.sh build-snapshot --slot <n>` is the explicit rebuild-from-source path.
2. The snapshot builder loads canonical parquet and image-catalog inputs into `catalog.*`, records
   seed versions in `ops.seed_state`, writes one `postgres_snapshot` metadata row, and emits a
   versioned `pg_dump` artifact plus manifest.
3. Normal `scripts/worktree/deps.sh ensure-postgres` and worktree bootstrap restore the latest
   snapshot artifact into a fresh slot-local Postgres volume instead of reseeding from canonical
   files.
4. `scripts/worktree/deps.sh reseed --slot <n>` remains the explicit maintenance workflow when a
   rebuild from canonical inputs is needed.
5. Query flow retrieves semantic matches directly from Postgres pgvector tables, then derives the
   candidate-set pair similarities for MMR directly in Postgres from `catalog.product_embeddings`.
6. Product-image lookup reads `catalog.product_images` and serves either backend-proxied URLs or
   direct public URLs based on config.

The build/bootstrap tooling above is intentionally outside `src/ikea_agent/`; application runtime
code consumes the prepared database state but does not own local dependency construction.

## Tool Sample Inputs
- Floor planner sample inputs live in typed tests under `tests/tools/test_floor_planner_*.py`.
- Inputs are modeled as centimeter-based Pydantic payloads.
- Generated floor-plan PNGs are runtime artifacts only and are not stored in git.

## Phase 2 References
- `spec/phase2/source_notes.md`
- `spec/phase2/ui_critique.md`

## Legacy

Historical SQL-driven schema/modeling artifacts are archived in `legacy/sql/`.
