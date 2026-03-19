# Postgres Snapshot Builds

## Purpose

Docker dependency bootstrap is moving away from rebuild-from-source during normal
startup. The durable contract is one explicit, versioned Postgres snapshot
artifact plus a manifest.

The snapshot artifact is a `pg_dump --format=custom` dump that already contains:

- migrated `app` tables required in a fresh local database
- `catalog.products_canonical`
- `catalog.product_embeddings` with pgvector data
- `catalog.product_images`
- `catalog.product_embedding_neighbors` when precomputed
- `ops.seed_state`, including a `postgres_snapshot` version row

## Local Build

Preferred developer entrypoint:

```bash
bash scripts/worktree/deps.sh build-snapshot --slot 7
```

That command builds the artifact under:

```text
<CANONICAL_ROOT>/.tmp_untracked/docker-deps/snapshots/<snapshot_version>/
```

Each versioned directory contains:

- `postgres.dump`
- `manifest.json`

The snapshot root also keeps `latest.json`, which points at the newest local
artifact and manifest.

### Local build steps

The builder:

1. starts an ephemeral pgvector-enabled Postgres builder stack
2. applies Alembic migrations
3. seeds catalog, embeddings, and image metadata
4. writes snapshot metadata into `ops.seed_state`
5. emits a custom-format `pg_dump`
6. restores that dump into a second fresh Postgres validator stack
7. checks counts, typed embedding reads, and image-catalog indexing

## CI Build

CI runs the same snapshot builder but uses the repo-local fixture image catalog
under `tests/fixtures/image_catalog/`. That keeps the workflow self-contained
while still validating the real dump/restore contract and runtime-facing table
shape.

Workflow:

- `.github/workflows/postgres-snapshot.yml`

Artifact naming:

- `postgres-snapshot-<snapshot_version>`

## Versioning

Snapshot versions are deterministic fingerprints over:

- Alembic migration head
- canonical Postgres seed fingerprint
- image catalog seed fingerprint
- snapshot-builder logic fingerprint
- embedding model
- configured neighbor-precompute limit

The manifest also records:

- build timestamp
- migration head
- builder fingerprint
- input fingerprints
- embedding model
- distance metric
- row counts
- artifact checksum and size
- restore-validation results
