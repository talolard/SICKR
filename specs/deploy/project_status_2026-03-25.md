# Deployment Project Status

Last updated: 2026-03-26

Read [guiding_principles.md](./guiding_principles.md) first.
The documents under `specs/deploy/` are the current source of truth for this
deployment project. Historical review documents and older deploy plans are
background only and must not override current workflow, Terraform, or runtime
contract reality.

Historical background only:

- [multi_agent_review.md](./multi_agent_review.md)
- older deploy plans under `plans/`, especially any plan that still assumes
  EC2, SSM, host deploy bundles, or manual ECS recovery as part of the normal
  deploy path

Cross-check current deploy claims against:

- `.github/workflows/`
- `infra/terraform/`
- [docs/deployment_runtime_contract.md](../../docs/deployment_runtime_contract.md)

## Current Canonical Direction

- The architecture direction is stable:
  `CloudFront + ALB + ECS Fargate + Aurora + S3`
- The repo is already past "first deploy still needs to happen."
- Aurora pause-to-zero is now a proven runtime behavior, not only a planned
  property.
- The deployed DB connection policy is settled:
  ECS backend uses the Aurora writer endpoint with `DATABASE_POOL_MODE = nullpool`.
- The real gap is now operational, not architectural:
  make the canonical `release -> publish -> deploy` path trustworthy without
  relying on manual recovery.
- The intended redeploy and rollback path is immutable release-tag redeploy via
  `release-deploy.yml`, not a source-ref build workflow.

Measured validation note:

- see
  [aurora_pause_to_zero_validation_2026-03-26.md](./aurora_pause_to_zero_validation_2026-03-26.md)

## What Is Implemented In The Repo Now

The repo now contains:

- production `ui` and `backend` Dockerfiles
- release-manifest generation
- `release-please`-driven release preparation on `release`
- migration stairway validation in PR CI and release validation
- ECS-oriented deploy workflows
- an ECS task-definition renderer
- Terraform modules for:
  - network
  - database
  - storage
  - edge
  - runtime
- a rewritten deploy spec set that treats Fargate+ALB as canonical

The old EC2-host deploy path has been removed from the repo surface:

- no host deploy bundle renderer
- no host-bundle runner
- no SSM command payload writer
- no production `docker compose` deploy file
- no host deploy env example
- no EC2 compute module

## What Is Still Untrustworthy

- The canonical release-publication lane is still not fully proven.
  `release-please` prepares release state, and publish now validates the merged
  Release Please PR head ref, merge commit, and final `vX.Y.Z` tag identity,
  but the end-to-end path still lacks a published immutable release record.
- `origin/release` already contains prepared release state through `0.4.0`, but
  the repo still has no published Git tags or GitHub releases. Prepared release
  state has moved ahead of published immutable release state.
- The current `main` copy of `.github/workflows/release-publish.yml` now uses
  the checked-in release-identity helper and plain `vX.Y.Z` tags, but that
  executable contract still needs real publication validation.
- The current deploy workflows still rediscover some ECS and ALB state live
  instead of consuming Terraform outputs end to end.

## Current Work Priorities

The current deploy priority order is:

1. workflow reliability
2. docs accuracy
3. release provenance
4. deploy visibility later, only after the existing path is trustworthy

## What This Makes Redundant

The following work should now be treated as obsolete, not as an alternate path:

- provisioning or debugging the single EC2 app host
- origin-host DNS for the app runtime
- SSM-based deploy workflows
- host-local rollback bookkeeping
- host-local compose orchestration
- any design that still assumes `nginx` or a host reverse proxy is required
- reintroducing a source-ref build-and-deploy workflow as a parallel
  steady-state path

## Current Goals

The next deploy slice should:

- make the normal release path trustworthy
- keep redeploy and rollback on immutable published release tags rather than a
  source-ref build lane
- align Release Please, immutable image tags, release manifest identity, and
  GitHub release publication
- keep the deploy contract automatic and fail-fast
- update docs before and after workflow changes so future work stops inheriting
  stale assumptions

## Current Recommended Sequence

1. Refresh `AGENTS.md` and the deploy specs so they describe the repo's actual
   state and current goals.
2. Treat older deploy epics and plans as historical unless explicitly
   refreshed.
3. Keep redeploy and rollback on immutable published release tags and remove
   any stale docs that still describe a source-ref deploy lane.
4. Simplify and repair the canonical `release -> publish -> deploy` flow.
5. Tighten release provenance so the immutable artifact record proves what was
   published.
6. Refresh the docs again after the workflow changes land.
