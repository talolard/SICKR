# Edge And App Routing

This subspec defines the public-path, CloudFront, ALB, and runtime-routing
contract for the near-term deployment.

Read [00_context.md](./00_context.md) first for shared deployment assumptions.
Read [10_cloudfront_product_images.md](./10_cloudfront_product_images.md) for
the static image path.
Read [25_ecs_fargate_alb_runtime.md](./25_ecs_fargate_alb_runtime.md) for the
managed runtime layer.
Read [70_bootstrap_migrations_and_readiness.md](./70_bootstrap_migrations_and_readiness.md)
for the readiness gates that validate this routing path before launch.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

The deployed app should present one public hostname and one same-origin browser
contract, but it should not pretend that all routes belong to the same runtime.

The required edge/origin shape is:

- CloudFront is the only public edge
- one ALB is the only application origin behind CloudFront
- the ALB routes `/ag-ui/*` to the backend service
- the ALB routes every other app path to the UI service
- product images use their own CloudFront-to-S3 behavior on the same hostname

## Stable Public Contract

The browser-visible contract must stay stable even if internal routing changes.

Required public-path ownership:

| Public path | CloudFront origin | Final owner | Notes |
| --- | --- | --- | --- |
| `/` and normal app pages | ALB | Next.js UI | SSR/app shell |
| `/_next/*` | ALB | Next.js UI | framework assets |
| `/api/copilotkit*` | ALB | Next.js UI | CopilotKit server routes in UI |
| `/api/attachments` | ALB | Next.js UI proxy | upload entrypoint must stay same-origin |
| `/attachments/*` | ALB | Next.js UI proxy | read/download entrypoint must stay same-origin |
| `/api/thread-data/*` | ALB | Next.js UI proxy | thread data proxy |
| `/api/agents*` | ALB | FastAPI backend | direct backend-owned metadata and agent list endpoints |
| `/api/health*` | ALB | FastAPI backend | direct backend health and readiness endpoints |
| `/api/traces*` | ALB | Next.js UI proxy | keep disabled in public v1 unless explicitly enabled |
| `/ag-ui/*` | ALB | FastAPI/AG-UI backend | direct SSE path after ALB path routing |
| `/static/product-images/*` | S3 image origin | static asset path | defined separately |

The rule is simple:

- if the browser already talks to a Next.js route today, keep that public path
  browser-stable and same-origin unless there is a clear simplification win in
  routing a backend-owned API straight to the backend
- `/ag-ui/*`, `/api/agents*`, and `/api/health*` should land on the backend
  service

## CloudFront Behavior Split

CloudFront should use exactly three behavior families.

Required path-pattern set:

- `/static/product-images/*`
- `/ag-ui/*`
- default `*`

### 1. Default App Behavior

Use the default behavior for normal app traffic routed to the ALB origin.

Required posture:

- target the ALB origin
- use a zero-cache policy such as `CachingDisabled`
- forward the request data needed for SSR, API routes, cookies, and auth state
- allow the HTTP methods needed by the app-origin routes
- do not treat the default behavior as a CDN cache for application responses

### 2. AG-UI Streaming Behavior

Use a dedicated `/ag-ui/*` behavior for the backend transport path.

Required posture:

- target the same ALB origin
- use a zero-cache policy such as `CachingDisabled`
- forwarding enabled for request method, headers, and body needed by AG-UI
- allow `POST`
- disable compression and response transformation on this behavior
- choose a read timeout that is comfortably larger than the backend heartbeat or
  packet cadence

This behavior remains a launch gate because AG-UI depends on streaming
correctness, not just correctness of final payload content.

### 3. Product-Image Behavior

Use `/static/product-images/*` for the S3-backed image origin.

This is already defined in
[10_cloudfront_product_images.md](./10_cloudfront_product_images.md) and should
remain independent from the dynamic app-origin behavior.

## ALB Routing Contract

The ALB is now the only application router behind CloudFront.

Required ALB rules:

- default listener action forwards to the UI target group
- one listener rule forwards `/api/agents*` to the backend target group
- one listener rule forwards `/api/health*` to the backend target group
- one listener rule forwards `/ag-ui/*` to the backend target group
- one backend-only listener on port `8000` forwards all paths to the backend
  target group for UI server-side proxy traffic

There is no required `nginx` layer in this architecture.

Internal routing rule:

- the browser never uses the backend-only ALB listener directly
- Next server proxy routes use `BACKEND_PROXY_BASE_URL`
- AG-UI client traffic uses `PY_AG_UI_URL`

## Why nginx Is Not Required

The older spec kept oscillating between direct origins and a host-local proxy.
The ALB removes that ambiguity:

- CloudFront no longer needs separate application hosts or ports
- the app no longer needs a reverse-proxy process just to split two HTTP paths
- one fewer buffering and timeout layer sits in the AG-UI streaming path

## SSE Safety Requirements

`/ag-ui/*` must still be treated as an SSE-sensitive route.

Required posture:

- no caching on `/ag-ui/*`
- no response transformation that waits for the full payload
- CloudFront timeout values comfortably larger than the backend heartbeat or
  packet cadence
- the backend must emit packets or heartbeats frequently enough to stay inside
  the configured CloudFront windows

Operational rule:

- if CloudFront or the ALB path causes AG-UI events to batch, stall, or
  truncate, the deployment is not launch-ready

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

## Health Contract

Required health surfaces:

- one backend liveness endpoint
- one backend readiness endpoint
- one UI liveness endpoint
- one UI readiness endpoint or equivalent proxy-safe app check

Recommended target-group checks:

- UI target group -> `/api/health/live`
- backend target group -> `/api/health/live`

The public readiness surface is `/api/health` served directly by the backend
through the ALB rule.

## Non-Goals

This subspec does not require:

- `nginx`
- multiple ALBs
- Cloud Map service discovery
- a separate public origin hostname just for the app runtime
