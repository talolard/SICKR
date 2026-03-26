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
- The manual ECS recovery lane exists in the repo today, but it is no longer a
  desired long-term path.

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

- The canonical release-publication lane is still weaker than intended.
  `release-please` prepares release state, but publication still depends on a
  separate handoff that is not yet strong enough.
- `origin/release` already contains prepared release state through `0.4.0`, but
  the repo still has no published Git tags or GitHub releases. Prepared release
  state has moved ahead of published immutable release state.
- The current `main` copy of `.github/workflows/release-publish.yml` is not a
  trustworthy executable contract because it contains a YAML parsing regression.
- The manual `manual-ref-deploy` lane is currently the more proven recovery
  path, but that is a sign of canonical-path weakness, not a desired steady
  state.
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
- keeping `manual-ref-deploy` as a parallel steady-state deploy path

## Current Goals

The next deploy slice should:

- make the normal release path trustworthy
- remove the manual ECS recovery lane and its docs/cross-links
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
3. Remove the manual ECS lane from the intended deploy design and its docs.
4. Simplify and repair the canonical `release -> publish -> deploy` flow.
5. Tighten release provenance so the immutable artifact record proves what was
   published.
6. Refresh the docs again after the workflow changes land.
