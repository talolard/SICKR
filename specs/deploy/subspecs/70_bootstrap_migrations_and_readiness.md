# Bootstrap, Migrations, And Readiness

This subspec defines the minimum deploy-time sequencing and launch gates for the
near-term deployment.

Read [00_context.md](./00_context.md) first for the shared deployment context.
Read [20_terraform_aws_setup.md](./20_terraform_aws_setup.md) for the AWS
primitives and [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md)
for the release artifact and deploy contract.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

This project needs two different operational flows:

- **environment bootstrap**
- **application deploy**

They must not be treated as the same thing.

A release is not live when containers start.
A release is live only after:

- the target database schema is migrated to head
- the required seeded catalog and image metadata already exist and verify as
  ready
- the backend is healthy enough to serve runtime traffic
- the UI can reach the backend over its configured internal URL

The key simplification is:

- normal app deploys do **not** rebuild or reseed the catalog from repo-side
  parquet and image-catalog inputs
- that heavy data-preparation path belongs to environment bootstrap, not to
  every release rollout

## Current Repo Reality

The repo already has concrete building blocks that this spec should use:

- runtime schema migrations use Alembic, as documented in
  [docs/data/migrations.md](../../docs/data/migrations.md)
- seed preparation already uses `scripts/docker_deps/seed_postgres.py`
- seed observability already exists through `ops.seed_state`
- the backend app already initializes persistence schema on startup
- the UI already has at least one health client, but the full deploy-grade
  backend readiness contract is not yet explicit

So the deployed system should formalize those existing pieces instead of
inventing a separate data model.

## Environment Bootstrap Policy

Environment bootstrap is required before first launch and any time the canonical
catalog inputs materially change.

Required bootstrap datasets:

- `catalog.products_canonical`
- `catalog.product_embeddings`
- `catalog.product_images`
- `ops.seed_state`

Bootstrap source of truth:

- canonical parquet and image-catalog inputs prepared by repo tooling
- image bytes uploaded to the public product-image bucket
- seed versions recorded in `ops.seed_state`

Required bootstrap behavior:

- bootstrap must be idempotent
- bootstrap may no-op if the required seed versions are already present
- bootstrap must record the resulting seed versions in `ops.seed_state`
- bootstrap seed versions must be content-based and stable across CI, local
  checkouts, and runtime environments; checkout path and file mtimes are not
  allowed inputs to the version hash
- bootstrap must prepare `catalog.product_images.public_url` for
  `direct_public_url` mode
- bootstrap is a separate workflow or one-off job, not a mandatory step inside
  every application release deploy

For v1, it is acceptable for this bootstrap to run from a dedicated operator
workflow or explicit one-off command sequence rather than from normal app deploy
automation.

Current operator entry point:

- `scripts/deploy/bootstrap_environment.sh`
  The operator script may run from a dedicated worktree while reading pinned
  parquet inputs from Tal's canonical checkout.

## Required Application Deploy Order

Every release deploy must follow this order:

1. Pull the exact `ui` and `backend` image digests selected by the release
   manifest.
2. Run database migrations against the target Aurora cluster.
3. Verify that required seed state and catalog/image metadata are already ready.
4. Start or restart the backend container.
5. Wait for backend liveness, then backend readiness.
6. Start or restart the UI container.
7. Wait for UI readiness and verify it can reach the backend.
8. Only then treat the release as live.

The deploy must fail closed.
If any migration, seed verification, or readiness step fails, the deploy is not
successful.

## Schema Migration Policy

Schema migrations are mandatory on every deploy.

Required policy:

- run `alembic upgrade head` or the equivalent image-bundled command before
  backend traffic is considered live
- migrations must target the real Aurora database, not a container-local DB
- migration success must be observable and fail the deploy if head is not
  reached
- additive persistence tables such as `app.revealed_preferences` must arrive
  through Alembic revisions, not through opportunistic runtime schema repair

Deploy rule:

- do not rely on app startup to opportunistically fix missing schema
- persistence schema creation in app startup is not a substitute for Alembic
  migration completion

## Seed Verification Policy

Steady-state deploy needs verification, not reseeding.

Required deploy-time verification:

- required `catalog.*` tables are populated
- `ops.seed_state` reflects a ready environment
- the expected `postgres_seed_version` is computed from stable content hashes
  rather than environment-specific file metadata
- if deployed image mode is `direct_public_url`, product-image metadata is ready
  for that mode
- the verification command fails loudly when the environment is not ready for
  the current app mode

This is intentionally lighter than environment bootstrap:

- deploy should verify that the data plane is ready
- deploy should not require repo-local parquet or image-catalog files on the
  host

## What Must Exist Before Live Traffic

Before the deploy is considered live, all of the following must be true:

- Alembic revision is at head
- required `catalog.*` seeded tables are populated
- `ops.seed_state` reflects a ready seed state
- if deployed image mode is `direct_public_url`, product-image metadata is ready
  for that mode
- backend can open database sessions and serve request traffic
- UI can call the backend over the configured internal URL

This is the minimum launch gate.

## Readiness Versus Liveness

The deploy needs two different health concepts.

### Liveness

Liveness answers only:

- is the process up
- is the container serving HTTP at all

Liveness should not depend on:

- a fully warmed Aurora cluster
- completed seed verification beyond basic startup
- successful end-to-end app traffic

Its job is to detect dead processes, not incomplete startup.

### Readiness

Readiness answers:

- can this release safely serve real traffic right now

Required backend readiness conditions:

- database connection succeeds
- schema revision is current
- required seed-state rows exist
- required seeded catalog and image metadata are available

Required UI readiness conditions:

- the UI process is up
- the UI can reach the backend REST proxy surface over `BACKEND_PROXY_BASE_URL`
- the UI can reach AG-UI over `PY_AG_UI_URL`
- the app can serve normal pages without immediate backend-path failure

## Required Health Endpoint Contract

This spec requires explicit health endpoints even though the full backend
contract is not fully implemented in the repo yet.

Required v1 endpoint posture:

- one backend liveness endpoint
- one backend readiness endpoint
- one UI-side health endpoint or equivalent readiness check

Minimum backend liveness contract:

- returns success if the backend process is up and routing is initialized
- must not perform heavy dependency checks

Minimum backend readiness contract:

- verifies database connectivity
- verifies schema is current enough for this release
- verifies required seed-state/data prerequisites are present

Minimum UI readiness contract:

- verifies the Next.js server is up
- verifies the UI can reach the backend over its configured internal URL

This spec does not lock down the exact route names.
It does require the distinction between liveness and readiness.

## Aurora Cold-Wake Tolerance

Aurora Serverless v2 may cold-wake after idle periods.
That is acceptable for this deployment, but the deploy and readiness contract
must account for it.

Required posture:

- readiness checks must retry through Aurora cold wake
- the first successful readiness check may take noticeably longer than a warm
  check
- the deploy must not declare failure on the first transient DB-connect timeout
  during the cold-wake window

Recommended v1 tolerance:

- allow up to 180 seconds for backend readiness during cold start or fresh
  deploy
- retry database-backed readiness checks with backoff inside that window

Measured validation on 2026-03-26:

- the live `ikea-agent-dev-db` Aurora writer sat at
  `ServerlessDatabaseCapacity = 0` and `ACUUtilization = 0` for several
  consecutive minutes while the ECS backend service stayed up
- a real readiness probe to
  `http://ikea-agent-dev-alb-1739844720.eu-central-1.elb.amazonaws.com/api/health/ready`
  then succeeded in `15.444` seconds and the same minute showed Aurora waking
  above zero capacity
- this validated the chosen runtime posture: deployed backend
  `DATABASE_POOL_MODE = nullpool`, plus retry/backoff in deploy readiness
  polling
- see
  [aurora_pause_to_zero_validation_2026-03-26.md](../aurora_pause_to_zero_validation_2026-03-26.md)

What is not acceptable:

- routing live traffic before readiness succeeds
- letting liveness restarts flap the backend during normal Aurora wake-up delay

## Minimum Launch Gates

The minimum launch gates for the first public deployment are:

1. migration step returns success
2. seed verification step returns success
3. backend liveness passes
4. backend readiness passes
5. UI readiness passes
6. one lightweight end-to-end app check succeeds

Recommended end-to-end app check:

- load one normal app page through the UI
- verify one backend-dependent route succeeds

This does not need to be a full smoke suite.
It does need to prove that the new release can actually serve traffic.

## Rollback Caveats

Application-image rollback is easy.
Database rollback is not.

Required policy:

- do not assume `alembic downgrade` is a normal deployment rollback path
- treat destructive or shape-changing migrations as forward-only unless proven
  otherwise
- if a release fails after an incompatible migration, prefer a forward fix or a
  controlled DB restore over an automatic downgrade

Near-term deploy rule:

- a rollback plan must be evaluated before merging migrations that delete,
  rewrite, or narrow live data

## Interaction With Other Subspecs

This subspec depends on and constrains other deploy specs:

- [20_terraform_aws_setup.md](./20_terraform_aws_setup.md)
  - Terraform must provide the Aurora database, secret access, and host runtime
    environment needed by the migration and readiness steps
- [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md)
  - CI/CD must treat migration, verification, and readiness as required deploy
    steps after image pull and before success
- [40_release_please_and_commit_policy.md](./40_release_please_and_commit_policy.md)
  - release versioning does not change the launch gates, but every tagged
    release must satisfy them before it is considered real

## What This Subspec Defers

This subspec intentionally does not decide:

- the exact helper scripts or CI step layout used to render and register ECS
  task-definition revisions
- the exact health endpoint route names
- the full zero-downtime deployment story
- the full observability dashboard and alert set
- the exact rollback runbook mechanics for destructive migrations
- the exact operator flow used for the one-off environment bootstrap

Those belong in later implementation or runbook work once the basic launch
contract is stable.

## Verification

When implemented, verify it with the following checks:

- confirm deploy always runs `alembic upgrade head` before live traffic
- confirm required `catalog.*` rows and `public_url` values are present after
  environment bootstrap
- confirm `ops.seed_state` reflects a ready environment
- confirm backend liveness can pass before readiness
- confirm backend readiness fails if DB connectivity or seed state is missing
- confirm UI readiness fails if the UI cannot reach the backend
- confirm a cold Aurora wake delays readiness but does not produce false
  success
- confirm the deploy is not marked successful until migration, seed
  verification, backend readiness, and UI readiness all pass

## Summary

The required v1 launch contract is:

- bootstrap the environment separately
- migrate on every deploy
- verify seeded data on every deploy
- start backend and wait for readiness
- start UI and wait for readiness
- tolerate Aurora cold wake without routing traffic early
- treat schema and seed prerequisites as hard launch gates
