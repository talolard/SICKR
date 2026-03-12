# Runtime DB Migrations

This project now uses Alembic + SQLAlchemy for runtime schema migrations.

## Configuration

- Alembic config: `alembic.ini`
- Migration scripts: `migrations/versions/`
- Runtime DB URL default:
  - derived from `DUCKDB_PATH` via SQLAlchemy DuckDB URL conversion
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

Use a throwaway DB file to validate migration bootstrapping:

```bash
ALEMBIC_DATABASE_URL="duckdb:///$(pwd)/.tmp_untracked/alembic_validation.duckdb" \
  uv run alembic upgrade head
```

If successful, the database should contain Alembic version metadata and no errors should be emitted.

## Current Room 3D Tables

Revision `20260306_0003` adds:

- `app.room_3d_assets`
  - thread-scoped OpenUSD asset bindings
  - links source uploaded asset ids to inspected USD metadata
- `app.room_3d_snapshots`
  - thread-scoped camera/lighting snapshot metadata
  - links persisted PNG snapshot assets to optional room_3d_asset bindings

## Current Analysis Input Table

Revision `20260312_0004` adds:

- `app.analysis_input_assets`
  - ordered source-of-truth links from one `analysis_runs` row to one or more uploaded image assets
  - preserves image ordinal for multi-photo analysis tools such as `get_room_detail_details_from_photo`
