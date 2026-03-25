# Migration Stairway Tests Plan

## Why

The repo currently has migration validation for:

- upgrading a fresh Postgres database to `head`
- upgrading when `app.revealed_preferences` already exists

That covers head bootstrap, but it does not cover the classic downgrade hygiene
problems that stairway tests are meant to catch:

- missing cleanup in `downgrade()`
- types, indexes, or extensions left behind in a way that breaks re-upgrade
- revision-by-revision assumptions that only fail once the chain is exercised

## External reference

The target pattern comes from Yandex's Alembic migration testing write-up:

- Query used: `Yandex stairway test migrations habr alembic`
- Source: `https://habr.com/ru/companies/yandex/articles/511892/`
- Relevant points:
  - use isolated databases for migration tests
  - template-backed databases are a good speed optimization
  - the core stairway test iterates revisions with `upgrade -> downgrade -> upgrade`

## Repo-specific design

### Test surface

Add a dedicated stairway test module under `tests/shared/` that:

- creates an isolated throwaway Postgres database
- resolves the Alembic revision chain from the repo's real `migrations/versions`
- runs per revision:
  - `upgrade` to that revision
  - `downgrade` one step back
  - `upgrade` to that revision again

This stays close to the Yandex pattern and uses the same Alembic config path as
runtime deployment.

### Populated database scenario

Also add one populated-database migration test that:

- seeds the slot database from the repo's CI fixture catalog
- clones that seeded database into a fresh throwaway database using PostgreSQL
  `CREATE DATABASE ... TEMPLATE ...`
- downgrades one step from `head`
- upgrades back to `head`

This is intentionally narrower than the clean-db stairway run. It is there to
catch migrations that are only safe on empty schema but fail against seeded
runtime-shaped data.

### CI contract

Add one dedicated PR CI job that:

- runs only when migration-relevant files change
- starts the repo's pgvector Postgres stack on a clean volume
- upgrades to `head` and seeds fixture catalog data deterministically
- runs the migration test suite against that Postgres instance
- tears the stack down

This intentionally avoids depending on a possibly stale published snapshot
artifact. Migration validation should fail on migration correctness, not on
artifact drift.

### Release contract

Add the same migration test suite to `release-publish.yml` before image
publication and release creation. If migration validation fails there, the
release must not publish.

## Validation plan

- targeted pytest for migration helpers and stairway tests
- targeted workflow lint-free validation by running the relevant pytest command
  locally against slot-backed Postgres
- `make tidy`
