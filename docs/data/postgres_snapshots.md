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
- `catalog.product_embedding_neighbors` only when explicitly materialized for legacy analysis flows
- `ops.seed_state`, including a `postgres_snapshot` version row

## Local Build

Preferred developer entrypoint:

```bash
bash scripts/worktree/deps.sh build-snapshot --slot 7
```

That command builds the artifact under:

```text
<CANONICAL_ROOT>/.tmp_untracked/shared-postgres/snapshots/<snapshot_version>/
```

Each versioned directory contains:

- `postgres.dump`
- `manifest.json`

The canonical shared snapshot root also keeps `latest.json`, which points at
the artifact and manifest currently preferred by bootstrap for every worktree in
the repo.

### Local build steps

The builder:

1. starts an ephemeral pgvector-enabled Postgres builder stack
2. applies Alembic migrations
3. seeds catalog, embeddings, and image metadata
4. writes snapshot metadata into `ops.seed_state`
5. emits a custom-format `pg_dump`
6. restores that dump into a second fresh Postgres validator stack
7. checks counts, typed embedding reads, and image-catalog indexing

## Normal Restore

Normal local startup now restores from the latest locally available snapshot
instead of reseeding from canonical files.

Primary entrypoint:

```bash
bash scripts/worktree/deps.sh ensure-postgres --slot 7
```

Restore behavior:

1. starts the repo-shared Postgres container on the shared local port
2. reads `latest.json` from the canonical shared snapshot cache
3. if the cache is empty or incomplete, attempts to fetch a published snapshot
   artifact from GitHub Actions into the canonical shared cache
4. restores the dump into the shared template database when the template is
   empty, stale, or missing snapshot metadata
5. clones one isolated worktree database from that template
6. runs Alembic `upgrade head` against the worktree database after clone verification

Explicit rebuild-from-source remains:

```bash
bash scripts/worktree/deps.sh reseed --slot 7
```

## CI Build

CI runs the same snapshot builder but uses the repo-local fixture image catalog
under `tests/fixtures/image_catalog/`. That keeps the workflow self-contained
while still validating the real dump/restore contract and runtime-facing table
shape.

This snapshot path is intentionally separate from the migration stairway lane.
The stairway tests seed a clean pgvector Postgres instance directly from fixture
catalog inputs so migration validation cannot fail just because a published
snapshot artifact drifted behind the current Alembic graph.

Workflow:

- `.github/workflows/postgres-snapshot.yml`

Artifact naming:

- `postgres-snapshot-<snapshot_version>`

Published artifact fetch command:

```bash
bash scripts/worktree/deps.sh fetch-snapshot
```

## Versioning

Snapshot versions are deterministic fingerprints over:

- Alembic migration head
- canonical Postgres seed fingerprint
- image catalog seed fingerprint
- snapshot-builder logic fingerprint
- embedding model
- optional legacy neighbor-precompute limit when such rows are explicitly materialized

The manifest also records:

- build timestamp
- migration head
- builder fingerprint
- input fingerprints
- embedding model
- distance metric
- neighbor-state strategy metadata
- row counts
- artifact checksum and size
- restore-validation results
