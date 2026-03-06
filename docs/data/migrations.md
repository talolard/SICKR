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
