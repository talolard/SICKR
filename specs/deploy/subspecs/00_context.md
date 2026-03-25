# Deployment Context

Read this document before reading the deployment subspecs in this directory.

These subspecs are a decomposition of the canonical parent deployment spec:
[final_deployment_recommendation_2026-03-24_synthesized.md](../final_deployment_recommendation_2026-03-24_synthesized.md).
That parent document is the top-level source of truth for the overall
deployment recommendation.
This file is the shared context layer for the focused subspecs under
`specs/deploy/subspecs/`.
Read [guiding_principles.md](../guiding_principles.md) for the standing
decision rules that should shape future epics, tasks, and implementation
choices.
Read [deployment_runtime_contract.md](../../docs/deployment_runtime_contract.md)
for the concrete deploy-time environment contract that later infra and CI
automation should consume.

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it
- stacked deployment work should continue to merge back toward
  `tal/deployproject` as the base branch for this project

## Purpose

These subspecs are for the near-term "share it with friends and get real
feedback" deployment.
We want a deployment that is simple, repeatable, cheap enough for very low
traffic, and easy to debug without babysitting a host.

## Goals

- keep the current product architecture intact
- keep the first internet-facing deployment cheap enough for a side project
- prefer automation and repeatability over the fastest possible first launch
- remove the EC2-host operational layer in favor of a simpler managed runtime
- avoid broad rewrites just to make hosting easier

## Current Application Shape

The current repo already has an important split:

- the browser talks to the Next.js app for many public routes
- the Next.js app proxies some of those requests to the Python backend
- the backend owns AG-UI, persistence-backed APIs, attachments, and product-image
  proxy routes

The important public-route reality is:

- `ui` owns `/`, `/_next/*`, `/api/copilotkit`, `/api/attachments`,
  `/attachments/*`, `/api/thread-data/*`, and `/api/traces*`
- `backend` owns `/ag-ui/*`, `/api/agents*`, and `/api/health*` directly at the
  public edge
- product images can be served either by backend proxy routes or by direct public
  URLs, depending on configuration

This split already exists in the app and should shape the deployment design.

## High-Level Decisions

For the near-term deployment, we are assuming:

- AWS account id `046673074482`
- one public app domain: `designagent.talperry.com`
- AWS region `eu-central-1` for the app plane
- `CloudFront + ALB + ECS Fargate + Aurora + S3` is now the canonical runtime
  shape
- CloudFront remains the public edge and CDN
- one ALB does the HTTP path split between `ui` and `backend`
- two ECS Fargate services run the application containers
- Aurora Serverless v2 is the preferred database direction because of
  scale-to-zero
- pause-to-zero is a desired property of the database tier; the app tier does
  not naturally scale to zero under Fargate
- static product images and dynamic private attachments should not be treated as
  the same storage problem
- semver tooling details live in a dedicated subspec
- Terraform and AWS shape live in a dedicated subspec

## Why We Pivoted Away From EC2

The EC2 design was workable, but it kept leaving behind a host-shaped surface:

- SSM-based deploy orchestration
- host bootstrap and package drift
- host-local rollback state
- host-local secret projection
- host-level compose and port wiring

That was directly at odds with the project goals of simplicity, automation, and
low ops burden.

The Fargate+ALB model is not cheaper at steady state, but it removes the host
class of problems entirely. For this project, that trade is acceptable if it
produces a more repeatable deployment system.

## Storage Posture

Shared storage posture for the near term:

- product images are static and can be public
- product images must be served from the public bucket/CDN path before launch;
  backend-proxy image serving is not acceptable for the deployed public path
- attachments and generated runtime artifacts are dynamic and should stay
  private in a separate bucket
- trace bundles remain developer-oriented and are not part of the first public
  rollout

## Release Posture

Shared release posture for the near term:

- `main` remains the normal integration branch
- releases are promoted from `main` to `release`
- `release-please` is the preferred semver and release-note automation mechanism
- release publication means:
  - immutable images were built and pushed
  - an immutable release manifest exists
  - an immutable Git tag and GitHub release were created
- deploy automation rolls those immutable artifacts onto ECS; it does not build
  on the runtime platform

## New Redundancies

Because the canonical runtime is now ECS Fargate plus ALB, these older EC2-host
surfaces are intentionally obsolete:

- the single EC2 app host
- origin-host DNS just for the app host
- SSM deploy payloads
- host-local deploy bundles
- host-local rollback bookkeeping
- `docker compose` as the production runtime substrate
- `nginx` as a required deployment layer

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
- `25_ecs_fargate_alb_runtime.md`
- `30_dockerization_and_cicd.md`
- `40_release_please_and_commit_policy.md`
- `50_edge_and_app_routing.md`
- `60_private_attachments_and_artifacts.md`
- `70_bootstrap_migrations_and_readiness.md`
- `80_logging_and_observability.md`
