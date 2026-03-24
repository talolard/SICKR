# Deployment Runtime Deployability Contract For `tal_maria_ikea-v9b.2`

## Summary

This slice tightens the application-side runtime contract that later deploy
automation and infra work will consume.

The goal is not to finish Terraform or release workflows.
The goal is to make the running app deploy-safe and to give the deployment
project concrete proof entrypoints for the two biggest technical risks:

- AG-UI streaming through the deployed path
- Aurora Serverless v2 pause-to-zero and cold-wake behavior

## Why This Slice Exists

The deploy specs already freeze the high-level public routing, health, and
bootstrap contract.
The repo also already contains some of the needed pieces:

- backend liveness and readiness routes
- deploy-time migration and bootstrap scripts
- a UI `/api/health` proxy
- Logfire bootstrap helpers

What is still missing is the tighter runtime posture that makes those pieces
usable by deploy automation instead of just usable for local development:

- explicit pause-friendly connection policy
- explicit retrying readiness wait entrypoint for Aurora cold wake
- explicit AG-UI streaming proof entrypoint
- startup and run-lifecycle logs that identify the running release
- a UI health surface that distinguishes "Next is up" from "the UI can reach the backend"

## Goals

- Keep the deployability contract in app/runtime code, not in infra code.
- Preserve the deploy spec rule that migrations and bootstrap are first-class
  deploy steps.
- Avoid app startup silently papering over missing Postgres schema.
- Make backend and UI health checks usable by future host deploy automation.
- Add proof entrypoints for readiness polling and AG-UI streaming validation.
- Keep logging sparse and operationally useful.

## Non-Goals

- No Terraform, CloudFront, or AWS resource changes.
- No release workflow or GitHub Actions changes.
- No nginx config changes in this slice.
- No full dress-rehearsal or public-hostname validation in this slice.

## Core Decisions

### 1. Use explicit connection-pool mode for deploys

The runtime should support a deploy-safe `NullPool` posture without changing the
local default.

Current decision:

- keep `queuepool` as the default for local/dev ergonomics
- add `DATABASE_POOL_MODE=nullpool` as the deploy recommendation
- thread this setting through runtime and deploy scripts

Why:

- it makes the Aurora pause-to-zero policy explicit
- it avoids hard-coding deploy behavior into every environment

### 2. Do not auto-bootstrap Postgres persistence schema on backend startup

Backend startup may still create missing SQLite tables for local tests and
one-off local runs.
For Postgres, the app should stop pretending that startup schema creation is a
valid deploy path.

Why:

- the deploy spec says Alembic completion is required before live traffic
- silent Postgres table creation hides migration drift instead of proving head

### 3. Deploy polling should live in a dedicated script, not in the HTTP route

The backend readiness route should stay a single probe.
Retry logic for Aurora cold wake belongs in a deploy-oriented polling script.

Why:

- health routes should stay fast and predictable
- deploy automation still needs a reusable retry/backoff entrypoint

### 4. AG-UI streaming proof should be a first-class script

The repo already has tests and debug UI for streaming.
This slice adds one deploy-oriented proof command that validates:

- HTTP 200
- `text/event-stream`
- at least one streamed chunk/event

Why:

- this is the main launch-risk proof path from the runtime side
- later public-path validation can call the same proof command against a host or domain

## Deliverables

- backend runtime config support for pool mode and deploy-safe startup behavior
- deploy polling script for HTTP readiness
- deploy proof script for AG-UI streaming
- explicit UI live/ready health routes
- targeted backend logging for startup and AG-UI run lifecycle
- updated deployment runtime contract docs and env examples
- focused tests for the new contract

## Validation Plan

- backend/unit tests for config, DB engine pool mode, and health behavior
- deploy-script tests for readiness polling and AG-UI stream proof helpers
- UI route tests for live/ready behavior
- `make tidy`

## Open Risks After This Slice

- This does not prove CloudFront or nginx SSE behavior yet.
- This does not prove Aurora pause-to-zero against a real Aurora cluster yet.
- UI proxy-route logging may still need wider standardization outside the health
  surface if production incidents show gaps.
