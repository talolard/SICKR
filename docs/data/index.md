# Data Model and Storage

## Active Runtime Stores

### Postgres (`DATABASE_URL`)

Active runtime uses Postgres for:
- `catalog.products_canonical` (seeded catalog metadata)
- `catalog.product_embeddings` (seeded embedding snapshots that feed Milvus)
- `catalog.product_embedding_neighbors` (optional precomputed cosine neighbors for MMR)
- `catalog.product_images` (seeded image metadata for runtime image lookup)
- `app.*` conversation and analysis tables managed by existing runtime migrations
- `ops.seed_state` (observable seed versions and refresh metadata)

### Shared Milvus (`MILVUS_URI`)

Active runtime uses one shared Milvus collection:
- `ikea_product_embeddings` (configurable)
- stores vector records used for semantic candidate retrieval

## Migrations

- Runtime schema migrations use Alembic + SQLAlchemy.
- See [Runtime DB Migrations](migrations.md) for commands and environment overrides.
- Local product-image serving and payload enrichment are documented in [Local Product Images](product_images.md).

## Data Lifecycle

1. Canonical parquet artifacts under `data/parquet/` and the shared image-catalog output root are
   the local seed inputs.
2. `scripts.docker_deps.seed_postgres` loads those inputs into `catalog.*` and records seed
   versions in `ops.seed_state`.
3. `scripts.docker_deps.prepare_milvus` hydrates the shared Milvus collection from
   `catalog.product_embeddings` and writes a local Milvus seed-state JSON file.
4. Query flow retrieves vector candidates from Milvus.
5. Postgres hydrates and filters candidates, then reads neighbor similarities from
   `catalog.product_embedding_neighbors` when present or computes them from stored embeddings when
   neighbor rows are absent.
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
