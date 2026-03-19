# Docker Deps Follow-ups

Date: 2026-03-19

## Goal

Apply the next architecture correction on top of the Postgres-only rollout:

1. use Gemini's original embedding width by default
2. replace the whole-product image preload layer with repository-backed lookups
3. replace remaining active runtime/tooling SQL text statements with SQLAlchemy query construction where the same behavior is available

## Findings

- The repo-local embedding snapshot needs to track Gemini's native width end to
  end, so runtime defaults, seeded parquet, and Postgres storage all have to
  move together.
- Preserving indexed retrieval at Gemini's native width requires the wider
  pgvector representation supported by the active Postgres index/operator path.
- Preloading the entire image table into memory just to serve a handful of URLs
  or local file paths is unnecessary once the seeded `catalog.product_images`
  table is already queryable through SQLAlchemy.
- Active retrieval/image code still carries SQL text statements in places that
  should now use SQLAlchemy table/query construction.

## Implementation Plan

### 1. Native embedding width and snapshot source

- Regenerate `data/parquet/product_embeddings` from the existing `embedded_text`
  payloads using the configured Gemini embedding API without down-projecting the
  output width.
- Move the shared embedding-width constant to the native Gemini size.
- Update runtime config defaults so query embeddings use that same width by default.
- Add or update tests that assert the configured width matches the repo's seeded
  embedding snapshot shape.

### 2. Pgvector schema/index update

- Move the Postgres embedding column/index definition to the pgvector storage type
  that supports the native Gemini width while preserving cosine-distance search.
- Add an Alembic migration that converts the existing column/index shape to the new
  one.
- Update retrieval schema tests and migration docs to reflect the new type and width.

### 3. Repository-backed image lookup

- Replace the whole-product image preload layer with direct repository queries for:
  - batched image URL lookup by canonical product key
  - local file resolution by `product_id` + ordinal for FastAPI image serving
- Add a composite lookup index for the active image-query access pattern.
- Update the search pipeline, bundle proposal hydration, runtime wiring, and image
  routes to use repository-backed lookups.
- Delete the catalog abstraction and its tests, replacing them with repository/route
  tests.

### 4. SQLAlchemy query cleanup

- Replace active catalog/runtime SQL text statements with SQLAlchemy-built selects,
  inserts, updates, and deletes where practical:
  - `src/ikea_agent/retrieval/catalog_repository.py`
  - `src/ikea_agent/retrieval/display_titles.py`
  - `scripts/docker_deps/seed_postgres.py`
- Leave unavoidable DDL-only bootstrap/migration helpers alone unless the change is
  trivial and clearly safer.

### 5. Docs and validation

- Update active docs/specs/config notes so they no longer recommend or describe
  SQL text statements as the preferred runtime path.
- Record the new embedding width and image-lookup behavior in the Postgres rollout
  docs.
- Validate with `make tidy` and `make ui-test-e2e-real-ui-smoke` before close.
