# Post-Launch Deploy Hardening Plan

Date: 2026-03-25
Epic: `tal_maria_ikea-v9b.8`
Branch: `epic/tal_maria_ikea-v9b-fix-live-api-agents-proxy-500-and-add-va`

## Why

The first live Fargate deploy worked, but only after manual recovery steps that
exposed four concrete contract bugs:

- seed-version fingerprints were environment-dependent
- release tooling disagreed on tag identity
- `app.revealed_preferences` was missing from the explicit migration path
- ECS publish/deploy automation still required manual cleanup and runtime
  knowledge

The live `/api/agents` 500 also showed that the UI proxy path was under-specified
and under-validated.

## Scope

This plan covers the remaining child tasks under `tal_maria_ikea-v9b.8`:

1. stabilize seed fingerprinting across environments
2. align release-please, Git tags, and release manifest identity
3. add explicit schema migration coverage for `app.revealed_preferences`
4. fold manual ECS recovery steps into publish/deploy automation
5. finish and deploy the live `/api/agents` proxy fix and make it launch-critical

## Implementation outline

### 1. Stable bootstrap fingerprinting

- replace mtime-based hashing with content-based hashing
- keep path-relative ordering stable and independent of checkout location
- share the same invariant between deploy-side helpers and seed/bootstrap code

### 2. Release identity cleanup

- remove the release-please component prefix so tag format is plain `vX.Y.Z`
- keep manifest validation, workflow tagging, and docs on the same invariant
- add tests where the current repo lacks explicit coverage

### 3. Explicit migration for revealed preferences

- add one Alembic revision for `app.revealed_preferences`
- update migration docs/tests so fresh Postgres environments prove the table
  exists without runtime repair

### 4. ECS automation hardening

- escape Alembic URLs correctly when passed through `Config.set_main_option`
- strip placeholder `sleep infinity` commands when rendering task definitions
- keep release/deploy workflows aligned with the rendered ECS contract

### 5. Live route validation and deployment

- keep the `BACKEND_PROXY_BASE_URL` fix as the explicit UI proxy contract
- validate `/api/agents` and `/api/agents/{agent}/metadata` in automation
- apply the runtime/network Terraform change if needed
- verify the public deployed paths directly on `designagent.talperry.com`

## Validation plan

- targeted pytest for release manifest, ECS rendering, seed/bootstrap helpers,
  migrations, and any new script behavior
- targeted Vitest for the Next proxy helper and route handlers
- `uv run alembic -c alembic.ini heads`
- `terraform validate` for touched runtime modules
- `make tidy`
- live endpoint verification after deploy for `/`, `/api/health`, `/api/agents`,
  `/api/agents/{agent}/metadata`, and AG-UI
