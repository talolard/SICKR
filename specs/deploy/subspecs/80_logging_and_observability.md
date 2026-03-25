# Logging And Observability

This subspec defines the default observability posture for the near-term
deployment.

Read [00_context.md](./00_context.md) first for the deployment scope.
Read [50_edge_and_app_routing.md](./50_edge_and_app_routing.md) for the proxy
and SSE path ownership this telemetry must describe.
Read [60_private_attachments_and_artifacts.md](./60_private_attachments_and_artifacts.md)
for the attachment and generated-artifact flows that need storage-boundary
signals.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) and
[70_bootstrap_migrations_and_readiness.md](./70_bootstrap_migrations_and_readiness.md)
for the deploy lifecycle this telemetry must support.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

Use Logfire as the default backend observability layer.

The deployment should lean on:

- Logfire tracing and log aggregation for backend runtime signals
- structured Next server-side runtime logs in container logs / CloudWatch
- targeted structured backend logs for operational facts
- lightweight frontend diagnostics only where they materially help
- existing AG-UI trace capture for deep debugging, not as an always-on log
  substitute

The goal is useful signals with low overhead, not maximal telemetry.

## Observability Layers

Use four distinct signal families and keep their jobs separate.

### 1. Request / Service Logs

Use for:

- startup
- shutdown
- migration, seed-verification, and environment-bootstrap outcomes
- upload/download outcomes
- upstream proxy failures
- agent-run start/complete/failure summaries

These should be sparse, structured, and human-readable.

### 2. Trace Spans

Use Logfire spans for:

- request timing
- FastAPI request boundaries
- pydantic-ai tool/agent execution
- important internal latency boundaries

These are the default place for timing and nested execution structure.

### 3. AG-UI Run Traces

The repo already persists canonical outbound AG-UI event traces and supports
developer trace bundles.

Use AG-UI traces for:

- detailed agent-run debugging
- developer incident investigation
- reconstructing one run’s streamed event history

Do not duplicate those event payloads into normal application logs.

### 4. Frontend Diagnostics

Use frontend diagnostics for:

- route/proxy failures visible only in the browser
- explicit user-triggered trace capture
- minimal error breadcrumbs for support/debug flows

Do not build a chatty always-on frontend log firehose in v1.

## Existing Instrumentation Baseline

The backend already has the right basic direction:

- Logfire bootstrap helpers exist
- `instrument_fastapi` is available
- `instrument_pydantic_ai` is available
- several agent toolsets already emit structured `logger.info(...)` events with
  stable telemetry context
- AG-UI runs are archived with `run_id`, `thread_id`, and serialized event trace
  payloads

That means this subspec is mostly about tightening patterns and filling obvious
gaps, not inventing a new observability stack.

## Default Stack Boundary

V1 should not add a separate direct browser Logfire SDK or a browser log
shipping pipeline.

Default rule:

- backend logs and traces go to Logfire by default
- Next server-side route logs must at least land in structured container logs
  that operators will check in CloudWatch
- browser diagnostics stay minimal and are emitted only through explicit app
  flows when needed
- AG-UI trace capture remains disabled in production-like deploys unless it is
  intentionally enabled

## Backend Logging Pattern

Backend logs should be structured event logs, not prose blobs.

Required log context fields where applicable:

- `request_id`
- `run_id`
- `thread_id`
- `agent_name`
- `attachment_id`
- `asset_kind`
- `release_version`
- `environment`

Required backend event families:

- app startup configured
- Logfire export enabled or disabled
- migration start / success / failure
- seed verification start / success / failure
- AG-UI run start / complete / failure
- attachment upload success / failure
- attachment read redirect/proxy failure
- upstream model/tool fallback events when they materially change behavior

Do not emit:

- one log line per SSE event chunk
- full request bodies
- full model prompts or full model outputs
- raw binary metadata dumps

## Where Backend Logging Needs To Improve

The repo already logs some tool-level starts and fallbacks.
The main missing backend logging areas for deployment are:

- startup configuration summary
- migration, seed-verification, and environment-bootstrap lifecycle
- attachment upload/download storage boundary
- UI-proxy-facing route failures that affect the public app
- release/version identity attached to startup and request handling

Those are the areas the deployment operator actually needs first.

## Next Route Handler Logging

The Next route handlers are an important operational logging surface because
they own several browser-stable paths while proxying backend behavior.

The deployment should add or standardize server-side logging around failures in:

- `/api/copilotkit`
- `/api/attachments`
- `/attachments/*`
- `/api/thread-data/*`
- `/api/agents*`
- `/api/traces*`

These logs should stay server-side and must include the same release-version
and environment tagging as backend logs. CloudWatch container logs are the
current required sink; forwarding them into Logfire later is a valid follow-on
improvement, not a v1 assumption.

When a Next proxy route fails, the log payload must also include enough routing
context to explain the failure without re-deriving env state from the task
definition:

- `backend_proxy_base_url`
- `ag_ui_base_url`
- `upstream_url`
- stable route id such as `/api/agents`

## Frontend Logging Pattern

The frontend should stay quiet by default.

Required frontend posture:

- no continuous browser-console shipping
- no raw prompt/attachment payload logging
- no duplicate copy of backend AG-UI event traces

What the frontend should capture:

- user-visible failures in app proxy routes
- fetch failures from `/api/copilotkit`, `/api/attachments`, `/api/thread-data`,
  and `/api/traces`
- explicit trace-save actions when the developer trace UI is enabled

Preferred frontend pattern:

- normalize errors into small typed failure events
- send them only when they add information the backend cannot already see

Frontend/browser code should prefer surfacing user-visible errors and letting
the server-side route handlers produce the durable operational logs.

## Relationship Between Logs, Spans, And Traces

Use this rule of thumb:

- logs answer: what happened
- spans answer: how long and where
- AG-UI traces answer: what the agent streamed during one run

Do not record the same event at full fidelity in all three systems.

Required separation:

- request and deploy lifecycle -> logs
- latency and nested work -> Logfire spans
- agent streaming event history -> AG-UI trace archive / saved trace bundle

## Minimum Required Deploy-Time Signals

The first public deployment needs at least these signals:

- backend startup log with release version and environment
- ui startup log with release version and environment
- migration outcome log
- seed verification outcome log
- attachment upload failures
- AG-UI run failures
- one backend health/readiness signal
- one ui health/readiness signal
- one deploy-time public-path check that covers `/api/agents` and
  `/api/agents/{agent}/metadata`
- one structured server-route failure log for any Next proxy failure, including
  the effective upstream URL and configured backend base URL

These signals should be enough to answer:

- did the new release boot
- did migration or seed verification fail
- is AG-UI failing broadly or only for a specific run
- are uploads/downloads broken
- which release version is currently emitting those failures

## Privacy Boundaries

Privacy must be explicit.

Do not log:

- attachment bytes
- presigned URL query strings
- full model prompts
- full model completions
- raw OAuth, API, or secret values
- full trace-bundle contents in normal logs

Allowed lightweight identifiers:

- `attachment_id`
- `run_id`
- `thread_id`
- `agent_name`
- storage object key only when needed for ops and not externally exposed

Saved trace bundles remain a developer-oriented tool and should stay gated,
redacted, and explicitly triggered.

## Low-Overhead Patterns

Preferred patterns:

- one start event and one terminal event for long operations
- small structured `extra={...}` payloads
- stable event names
- reuse existing telemetry context helpers
- let Logfire spans carry timing detail instead of logging elapsed time at every
  sub-step

Avoid:

- chatty debug logging in hot paths
- per-token or per-chunk logging
- serializing large payloads into log lines
- frontend console mirroring in normal operation
- logging and tracing the same payload in full

## Recommended Backend Additions

The deployment should add or standardize these backend events:

- `backend_startup_complete`
- `migration_upgrade_started`
- `migration_upgrade_succeeded`
- `migration_upgrade_failed`
- `seed_verification_started`
- `seed_verification_succeeded`
- `seed_verification_failed`
- `attachment_upload_succeeded`
- `attachment_upload_failed`
- `attachment_read_failed`
- `next_proxy_request_failed`
- `agui_run_started`
- `agui_run_completed`
- `agui_run_failed`

Exact names can vary, but keep them stable once chosen.

## Recommended Frontend Additions

The deployment should add or standardize these frontend-side signals:

- normalized error reporting for failed proxy fetches
- route-local logging around attachment upload failures
- route-local logging around trace-save failures
- release version attached to any emitted frontend diagnostic event

Do not turn normal user interaction into a verbose frontend analytics stream.

## Verification

When implemented, verify the observability posture with these checks:

- confirm backend startup logs include `release_version` and `environment`
- confirm migration, seed verification, and one-off bootstrap success/failure
  are visible in Logfire
- confirm Next route-handler proxy failures are visible in Logfire
- confirm AG-UI run failures are visible without per-chunk log spam
- confirm attachment upload/read failures are visible without logging bytes or
  presigned URL query strings
- confirm production-like deploys do not expose developer trace capture unless
  it is intentionally enabled

## Explicit Deferrals

This subspec intentionally does not decide:

- a full metrics backend beyond what Logfire already gives us
- real-user monitoring
- browser session replay
- high-cardinality business analytics
- long-term retention tuning
- alert routing policy
- a complete dashboard set

Those are later hardening steps, not launch blockers.

## Summary

The required v1 observability posture is:

- Logfire is the default backend and Next server-side tracing/log aggregation
  layer
- backend logs are sparse, structured, and deployment-focused
- frontend diagnostics stay minimal and intentional
- AG-UI traces remain the detailed debugging tool for one run
- privacy wins over verbosity
- deployment success depends on a small set of clear startup, readiness, upload,
  and AG-UI signals
