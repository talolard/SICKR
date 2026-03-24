# Edge And App Routing

This subspec defines the public-path, CloudFront, and origin-routing contract
for the near-term deployment.

Read [00_context.md](./00_context.md) first for shared deployment assumptions.
Read [10_cloudfront_product_images.md](./10_cloudfront_product_images.md) for
the static image path.
Read [60_private_attachments_and_artifacts.md](./60_private_attachments_and_artifacts.md)
for the private attachment route contract this edge layer must preserve.
Read [70_bootstrap_migrations_and_readiness.md](./70_bootstrap_migrations_and_readiness.md)
for the readiness gates that validate this routing path before launch.
Read [20_terraform_aws_setup.md](./20_terraform_aws_setup.md) for the AWS
resource shape that this routing plan sits on top of.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

The deployed app should present one public hostname and one same-origin browser
contract, but it should not pretend that all routes belong to the same runtime.

The required edge/origin shape is:

- CloudFront is the only public edge
- `nginx` is the only app origin reverse proxy
- `ui` handles browser-facing Next.js routes
- `backend` handles only the direct AG-UI transport path
- product images use their own CloudFront-to-S3 behavior on the same hostname

Current code review confirms that this split already exists:

- `ui` owns `/api/copilotkit` and `/api/copilotkit/info`
- `ui` owns `/api/attachments`
- `ui` owns `/attachments/*`
- `ui` owns `/api/thread-data/*`
- `ui` owns `/api/agents*`
- `ui` owns `/api/traces*`
- `ui` also contains `/api/agui-run`, but that route is a debug helper and is
  not part of the public deployment contract
- `backend` owns `/ag-ui/*`
- `backend` also exposes `/attachments`, `/api/agents`, `/api/traces`, and
  `/static/product-images/*` as internal upstream routes

## Stable Public Contract

The browser-visible contract must stay stable even if internal routing changes.

Required public-path ownership:

| Public path | Origin target | Owner | Notes |
| --- | --- | --- | --- |
| `/` and normal app pages | `ui` via `nginx` | Next.js | SSR/app shell |
| `/_next/*` | `ui` via `nginx` | Next.js | framework assets |
| `/api/copilotkit*` | `ui` via `nginx` | Next.js | CopilotKit server routes in UI |
| `/api/attachments` | `ui` via `nginx` | Next.js proxy | upload entrypoint must stay same-origin |
| `/attachments/*` | `ui` via `nginx` | Next.js proxy | read/download entrypoint must stay same-origin |
| `/api/thread-data/*` | `ui` via `nginx` | Next.js proxy | thread data proxy |
| `/api/agents*` | `ui` via `nginx` | Next.js proxy | metadata proxy |
| `/api/traces*` | `ui` via `nginx` | Next.js proxy | keep disabled in public v1 unless explicitly enabled |
| `/ag-ui/*` | `backend` via `nginx` | FastAPI/AG-UI | direct SSE path |
| `/static/product-images/*` | S3 image origin via CloudFront | static asset path | defined separately |

The rule is simple:

- if the browser already talks to a Next.js route today, keep that public path
  browser-stable and same-origin
- only `/ag-ui/*` should bypass the UI container and go straight to the backend

Debug-only paths such as `/api/agui-run` or `/debug/*` are not part of the
internet-facing contract and may be disabled in deployed environments.

## CloudFront Behavior Split

CloudFront should use exactly three behavior families.

Required path-pattern set:

- `/static/product-images/*`
- `/ag-ui/*`
- default `*`

### 1. Default App Behavior

Use the default behavior for normal app traffic routed to the EC2 origin.

Required posture:

- target the `nginx` app origin
- use a zero-cache policy such as `CachingDisabled` or an equivalent custom
  policy
- forward the request data needed for SSR, API routes, cookies, and auth state
- allow the HTTP methods needed by the app-origin routes, including `POST` and
  `PATCH`
- do not treat the default behavior as a CDN cache for application responses

This behavior must be appropriate for:

- app pages
- `/_next/*`
- Next.js API routes

Do not create extra CloudFront behaviors for `/_next/*` or generic `/api/*` in
v1. The point of this subspec is one simple dynamic app behavior plus one AG-UI
streaming behavior.

### 2. AG-UI Streaming Behavior

Use a dedicated `/ag-ui/*` behavior for the backend transport path.

Required posture:

- target the same `nginx` app origin
- use a zero-cache policy such as `CachingDisabled`
- forwarding enabled for request method, headers, and body needed by AG-UI
- allow `POST`
- CloudFront-to-origin transport stays on the normal custom-origin HTTP path
- response timeout must be comfortably larger than the backend heartbeat or
  packet cadence
- response completion timeout should be left unset in v1 so CloudFront does not
  impose a hard maximum stream length

This behavior is a launch gate because AG-UI depends on streaming correctness,
not just correctness of final payload content.

### 3. Product-Image Behavior

Use `/static/product-images/*` for the S3-backed image origin.

This is already defined in
[10_cloudfront_product_images.md](./10_cloudfront_product_images.md) and should
remain independent from the dynamic app-origin behavior.

## nginx Origin Routing

`nginx` is the only public origin behind CloudFront and must make the final
local routing choice between `ui` and `backend`.

Required local routing rules:

- route `/ag-ui/*` to the `backend` container
- route `/`, `/_next/*`, and `/api/copilotkit*` to the `ui` container
- route `/api/attachments`, `/attachments/*`, `/api/thread-data/*`,
  `/api/agents*`, and `/api/traces*` to the `ui` container
- never send browser-visible `/api/attachments` or `/attachments/*` directly to
  the backend from CloudFront
- do not terminate product-image requests inside `nginx`; let CloudFront send
  them to the image origin instead

`nginx` should stay thin:

- path-based routing
- no business logic
- no content rewriting beyond the minimal proxy contract

## SSE Safety Requirements

`/ag-ui/*` must be treated as an SSE-sensitive route.

Required SSE safety posture:

- no proxy buffering on the `nginx` path for `/ag-ui/*`
- no compression or response transformation on the `/ag-ui/*` proxy path
- no response transformation that waits for the full payload
- HTTP/1.1 semantics preserved to the origin path
- read timeout values comfortably larger than the backend heartbeat or packet
  cadence
- caching disabled end to end
- the backend must emit packets or heartbeats frequently enough to stay inside
  the configured CloudFront and `nginx` read-timeout windows

Operational rule:

- if `nginx` or CloudFront causes AG-UI events to batch, stall, or truncate, the
  deployment is not launch-ready
- if the backend goes silent longer than the configured read timeout and
  CloudFront drops the `POST`, that is a deployment bug, not an accepted v1
  limitation

This spec intentionally does not lock exact timeout numbers yet, but it does
require explicit streaming validation before launch.

## Cache And Header Posture

Required cache posture by path family:

- `/static/product-images/*`: long-lived CDN caching, immutable object keys
- `/ag-ui/*`: no caching
- all other app/API routes: effectively no caching unless a route explicitly
  opts in

Required header posture:

- preserve cookies and request context for Next.js-owned dynamic routes
- preserve the request method and streaming semantics for `/ag-ui/*`
- do not forward unnecessary viewer state to the image origin

## Origin Health Contract

The deployed stack needs a small explicit health contract even though exact
endpoint implementation is still separate work.

Required health surfaces:

- one backend liveness endpoint
- one backend readiness endpoint
- one UI readiness endpoint or equivalent proxy-safe app check
- one origin-level `nginx` health endpoint that can be used by deployment checks

Current repo note:

- UI helper code expects `/api/health`, but this repo does not yet define that
  route in the deployed Next app
- treat the health routes as required implementation work, not as already
  finished behavior

Required liveness rule:

- backend liveness must verify only that the backend process is up and routing
  is initialized
- it must not depend on database reachability

Required readiness rule:

- backend readiness is the database-aware and seed-aware check
- `nginx` is not considered ready until both `ui` and backend readiness are
  reachable
- the deployment is not considered live until the backend streaming path and one
  normal UI path both succeed

## Environment Wiring

This routing spec depends on a few environment-level contracts.

Required wiring:

- `PY_AG_UI_URL` points the UI container at the backend AG-UI base URL
- Next.js proxy routes continue to use `PY_AG_UI_URL` for backend forwarding
- `NEXT_PUBLIC_USE_MOCK_AGENT=0` in deployed environments
- `NEXT_PUBLIC_TRACE_CAPTURE_ENABLED=0` in deployed environments unless trace
  capture is explicitly turned on

## What This Subspec Defers

This subspec intentionally does not decide:

- the exact `nginx` config file contents
- the exact CloudFront timeout numbers for `/ag-ui/*`
- whether CloudFront talks to the origin over HTTP or HTTPS
- WAF and stricter origin-hardening policy
- the exact health endpoint URLs

Those are implementation details, but the routing ownership and SSE constraints
above are not optional.

## Verification

When implemented, verify the routing contract with these checks:

- confirm `/_next/*`, `/api/copilotkit*`, `/api/attachments`, `/attachments/*`,
  `/api/thread-data/*`, `/api/agents*`, and `/api/traces*` all resolve through
  the `ui` container path
- confirm one normal page load succeeds through the public hostname
- confirm `/ag-ui/*` resolves through the backend path
- confirm `/static/product-images/*` is served from the image origin behavior
- confirm `/ag-ui/*` streams progressively through `CloudFront -> nginx ->
  backend` without buffering
- confirm a deliberately long AG-UI run keeps streaming without a read-timeout
  disconnect
- confirm a browser attachment upload still posts to `/api/attachments`
- confirm a browser attachment read still uses `/attachments/{id}`

## Summary

The public edge and origin-routing contract is:

- one same-origin public hostname
- CloudFront at the edge
- `nginx` as the only app origin
- `ui` keeps the browser-facing Next.js route set
- `backend` owns only `/ag-ui/*`
- product images stay on their own static behavior
- SSE correctness for `/ag-ui/*` is a launch gate
