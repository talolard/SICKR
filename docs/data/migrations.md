# Runtime DB Migrations

This project now uses Alembic + SQLAlchemy for runtime schema migrations.

## Configuration

- Alembic config: `alembic.ini`
- Migration scripts: `migrations/versions/`
- Runtime DB URL default:
  - `DATABASE_URL=postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent`
  - override for one-off runs with `ALEMBIC_DATABASE_URL`

## Common Commands

Run from repository root.

```bash
# Upgrade target DB to latest revision
uv run alembic upgrade head

# Create a new revision scaffold
uv run alembic revision -m "describe change"

# Downgrade one revision
uv run alembic downgrade -1
```

## Clean DB Validation

Use a throwaway local Postgres database or one slot-scoped worktree database to validate
migration bootstrapping:

```bash
scripts/worktree/deps.sh reset --slot 7

ALEMBIC_DATABASE_URL="postgresql+psycopg://ikea:ikea@127.0.0.1:15439/ikea_agent" \
  uv run alembic upgrade head
```

If successful, the database should contain Alembic version metadata plus the expected `app`,
`catalog`, and `ops` schemas, and no errors should be emitted.

If the slot was created before the pgvector change, use `reset` once so Docker recreates the
Postgres container from the pgvector-capable image.

## Current Catalog And Seed Tables

Revision `20260319_0005` adds:

- `catalog.products_canonical`
  - seeded product metadata used for runtime hydration
- `catalog.product_embeddings`
  - embedding snapshot source used for runtime pgvector retrieval
- `catalog.product_embedding_neighbors`
  - optional legacy precomputed neighbor similarities; active MMR now derives candidate-set
    similarities directly from `catalog.product_embeddings`
- `catalog.product_images`
  - seeded product-image metadata used by runtime image lookup
- `ops.seed_state`
  - observable seed versions and refresh details for local dependency preparation
  - also stores `postgres_snapshot` version metadata before snapshot dumps are emitted

Revision `20260319_0006` adds:

- PostgreSQL `vector` extension creation for local Dockerized Postgres
- conversion of `catalog.product_embeddings.embedding_vector` from `DOUBLE PRECISION[]` to
  `VECTOR(256)`
- HNSW ANN index on `catalog.product_embeddings.embedding_vector` using cosine distance

Revision `20260319_0007` adds:

- conversion of `catalog.product_embeddings.embedding_vector` from `VECTOR(256)` to
  `HALFVEC(3072)` so the active schema stores native-width Gemini embeddings while keeping
  HNSW cosine search indexed in Postgres
- conversion of existing local `VECTOR(256)` rows by padding them during migration so older
  volumes can upgrade in place before a fresh snapshot restore
- composite product-image lookup indexes for the active ORM access paths:
  - `catalog.product_images(product_id, is_og_image, image_rank, image_asset_key)`
  - `catalog.product_images(canonical_product_key, is_og_image, image_rank, image_asset_key)`

## Current Room 3D Tables

Revision `20260306_0003` adds:

- `app.room_3d_assets`
  - thread-scoped OpenUSD asset bindings
  - links source uploaded asset ids to inspected USD metadata
- `app.room_3d_snapshots`
  - thread-scoped camera/lighting snapshot metadata
  - links persisted PNG snapshot assets to optional room_3d_asset bindings

## Current Analysis Input Link Table

Revision `20260312_0004` adds:

- `app.analysis_input_assets`
  - ordered source-asset links for one `analysis_runs` row
  - preserves request image order for multi-image tools such as
    `get_room_detail_details_from_photo`
  - keeps relational integrity between persisted analyses and uploaded source assets
