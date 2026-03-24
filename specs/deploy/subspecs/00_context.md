# Deployment Context

Read this document before reading the deployment subspecs in this directory.

These subspecs are a decomposition of the canonical parent deployment spec:
[final_deployment_recommendation_2026-03-24_synthesized.md](../final_deployment_recommendation_2026-03-24_synthesized.md).
That parent document is the top-level source of truth for the overall deployment
recommendation.
This file is the shared context layer for the focused subspecs under
`specs/deploy/subspecs/`.
Read [guiding_principles.md](../guiding_principles.md) for the standing
decision rules that should shape future epics, tasks, and implementation
choices.
Read [deployment_runtime_contract.md](../../docs/deployment_runtime_contract.md)
for the concrete deploy-time environment contract that later infra and host
automation should consume.

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it
- stacked deployment work should continue to merge back toward
  `tal/deployproject` as the base branch for this project

Its job is to hold the shared context so later subspecs can stay focused and do
not have to repeat the same background.

## Purpose

These subspecs are for the near-term "share it with friends and get real
feedback" deployment.
We want to deploy this to show friends, but we don't need full production grade or scale.
Notably, this will be accessed at low volume, for only a few hours a day, not even all days.
Conversely, we do want automation where it can be done once and simply, so that deploys and updates are fast and simple.
Because this is a single-developer project, repeatable and correct automation is
preferred over a one-off fast launch path.

## Goals

- keep the current product architecture intact
- keep the first internet-facing deployment cheap and simple
- make the deployment coherent enough that individual infra decisions can be
  speced separately
- avoid broad rewrites just to make hosting easier

## Current Application Shape

The current repo already has an important split:

- the browser talks to the Next.js app for many public routes
- the Next.js app proxies some of those requests to the Python backend
- the backend owns AG-UI, persistence-backed APIs, attachments, and product-image
  proxy routes

The important public-route reality is:

- `ui` owns `/`, `/_next/*`, `/api/copilotkit`, `/api/attachments`,
  `/attachments/*`, `/api/thread-data/*`, `/api/agents*`, and `/api/traces*`
- `backend` owns `/ag-ui/*` directly
- product images can be served either by backend proxy routes or by direct public
  URLs, depending on configuration

This split already exists in the app and should shape the deployment design.

## High-Level Decisions

For the near-term deployment, we are assuming:

- AWS account id `046673074482`
- one public app domain
- no product rewrite
- Aurora Serverless v2 is the preferred database direction, because of scale-to-zero
- pause-to-zero is a desired property of the low-duty-cycle deployment
- `RDS Proxy` is out for this use case
- static product images and dynamic private attachments should not be treated as
  the same storage problem
- semver tooling details live in a dedicated subspec
- Terraform and AWS shape live in a dedicated subspec

## Storage Posture

Shared storage posture for the near term:

- product images are static and can be public
- product images must be served from the public bucket/CDN path before launch;
  backend-proxy image serving is not acceptable for the deployed public path
- attachments and generated runtime artifacts are dynamic and should stay private (different bucket)
- trace bundles remain developer-oriented and are not part of the first public
  rollout

## Release Posture

Shared release posture for the near term:

- `main` remains the normal integration branch
- We release from a release branch (that is tagged) it is a promotion branch from `main`
- app-level semver is acceptable
- release-please is the preferred semver and release-note automation mechanism
- the implemented release automation now consists of:
  - `.github/workflows/pr-title-main.yml`
  - `.github/workflows/release-please.yml`
  - `.github/workflows/release-publish.yml`
- release-tooling and commit-policy details live in a dedicated subspec
- full release and deploy automation is a first-class project goal, not
  post-launch polish

## Authoring Rule For Subspecs

Future deployment subspecs should:

- reference this file for shared goals and assumptions
- state only the focused decision they are making
- avoid repeating the full architecture and motivation unless the focus really
  needs it

## Current Subspecs

- `00_context.md`
- `10_cloudfront_product_images.md`
- `20_terraform_aws_setup.md`
- `30_dockerization_and_cicd.md`
- `40_semantic_release_and_commit_policy.md`
- `50_edge_and_app_routing.md`
- `60_private_attachments_and_artifacts.md`
- `70_bootstrap_migrations_and_readiness.md`
- `80_logging_and_observability.md`
