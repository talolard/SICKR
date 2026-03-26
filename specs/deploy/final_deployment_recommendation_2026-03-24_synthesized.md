# Synthesized Deployment Review And Revised Recommendation

This document is the canonical top-level deployment spec for the near-term
public deployment.
The focused specs in [subspecs/](./subspecs/) decompose this document into
implementation-facing areas.
Read [subspecs/00_context.md](./subspecs/00_context.md) before reading the
individual subspecs.

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it

## Scope

This is not the full Terraform implementation and not the final launch runbook.
Its job is to state the correct cohesive deployment picture so the subspecs and
tasks can decompose it consistently.

Current repo-state note:

- one live ECS Fargate deploy has already happened
- the repo is in post-cutover hardening, not pre-cutover architecture selection
- this document defines the desired steady-state contract, not a claim that the
  current workflows already satisfy it end to end

## Canonical Recommendation

Use this topology:

- one `CloudFront` distribution as the public edge
- one ACM certificate attached to CloudFront
- one public hostname: `designagent.talperry.com`
- one public `ALB` as the application origin behind CloudFront
- one `ui` ECS Fargate service running Next.js
- one `backend` ECS Fargate service running FastAPI + PydanticAI + AG-UI
- Aurora Serverless v2 PostgreSQL
- one public S3 bucket for product images
- one private S3 bucket for attachments and generated runtime artifacts

This replaces the older single-EC2-host deploy model.

## Why This Is The Better Shape

For this project, the priority order is:

- simplicity
- automation
- repeatability
- easy debugging
- then cost optimization inside those constraints

The EC2 design kept dragging a machine-management layer along with it:

- host bootstrap
- package drift
- SSM command orchestration
- host-local compose state
- host-local rollback state

The Fargate+ALB design removes that entire class of problems. It is not the
lowest steady-state cost option, but it is the cleaner operational system for a
single-developer side project.

## Public Routing Model

The browser-visible contract remains:

- `ui` owns `/`, `/_next/*`, `/api/copilotkit`, `/api/attachments`,
  `/attachments/*`, `/api/thread-data/*`, and `/api/traces*`
- `backend` owns `/ag-ui/*`, `/api/agents*`, and `/api/health*`
- product images live at `/static/product-images/*`

The routing layers should enforce that split like this:

- CloudFront default behavior -> ALB
- CloudFront `/ag-ui/*` behavior -> same ALB, no-cache, streaming-safe
- CloudFront `/static/product-images/*` behavior -> S3 image origin
- ALB default listener action -> UI target group
- ALB `/ag-ui/*` listener rule -> backend target group

There is no required `nginx` layer.

## Database

Use Aurora Serverless v2 PostgreSQL, on the latest Aurora PostgreSQL version
that supports `pgvector`.

Policy:

- commit to pause-to-zero
- keep `idle_session_timeout = 15 minutes`
- keep application connection handling pause-friendly
- do not add `RDS Proxy`

If pooled connections prevent reliable pause-to-zero, prefer `NullPool` in the
deployed runtime.

## Storage

Keep the storage split by artifact family:

- product images are static and public
- attachments and generated runtime artifacts are dynamic and private

Product images:

- live in the public bucket
- are fronted by CloudFront
- are exposed at `/static/product-images/*`
- are seeded into the catalog as same-host `public_url` values

Attachments and generated artifacts:

- live in the private bucket
- keep stable IDs in durable state
- are resolved at request time through app-owned same-origin routes

## Release And Deployment Model

Use one application-level version per deployable release.

The release flow should be:

1. releasable changes land on `main` with conventional-commit intent
2. releasable history is promoted from `main` to `release` without squashing
   away the commit semantics that `release-please` analyzes
3. `release-please` prepares the release PR and release version on `release`
4. CI uses that release version to build and push the `ui` and `backend`
   images under immutable version and commit tags
5. CI writes one release manifest containing the pinned digests and bootstrap
   metadata
6. CI creates the immutable Git tag and GitHub release only after image
   publication and manifest creation succeed
7. the same canonical release flow deploys automatically to ECS
8. deploy automation renders new ECS task-definition revisions from the current
   Terraform-owned baseline
9. deploy automation runs one-off backend migration and seed-verification tasks
   on Fargate
10. deploy automation updates the backend ECS service
11. deploy automation updates the UI ECS service

There should be no host-local deploy bundle, no SSM command payload, and no
host-local rollback bookkeeping.

Rollback means redeploying an older immutable release tag through the same ECS
workflow.

## Bootstrap Versus Steady State

One-off environment bootstrap is still separate from steady-state app deploy.

One-off bootstrap includes:

- initial schema bring-up if needed
- canonical seed/bootstrap flow
- catalog image metadata seeding

Steady-state deploy includes:

- migrations
- seed verification
- ECS service rollout

Normal deploys should not re-run catalog bootstrap.

## Remaining Pre-Launch Work

This architecture choice does not make the project launch-ready by itself.
Before first public launch we still need:

- a trustworthy canonical `release -> publish -> deploy` flow that does not
  depend on manual recovery
- release provenance that ties Release Please state, image tags, release
  manifest, and GitHub release publication together cleanly
- Terraform, workflow docs, and runtime contract docs that all describe the
  same deploy shape
- one real proof of AG-UI streaming through `CloudFront -> ALB -> backend`
- one real proof of Aurora pause-to-zero with the deployed connection policy
- one one-off environment bootstrap for the target database
- product images uploaded to the public bucket before launch

## Summary

The canonical deployment story is now:

- `CloudFront + ALB + ECS Fargate + Aurora + S3`

The EC2/SSM/compose path is obsolete and should be removed rather than kept as
a parallel option.
