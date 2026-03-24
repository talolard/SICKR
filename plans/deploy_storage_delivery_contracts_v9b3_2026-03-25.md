# Deploy Storage Delivery Contracts v9b.3

## Summary

Implement the app-side storage and delivery contract for deployment epic
`tal_maria_ikea-v9b.3`.

This slice covers two deployment-facing behaviors:

- product images must use deterministic same-host direct public URLs in
  deployed `direct_public_url` mode
- private attachments and generated artifacts must keep stable
  `/attachments/{attachment_id}` application routes while durable state stores
  opaque storage locators instead of expiring URLs

## Why This Exists

The deploy specs under `specs/deploy/` freeze two launch requirements that the
current app only partially satisfies:

- product-image direct delivery is selected in config and docs, but the runtime
  still assumes `catalog.product_images.public_url` was seeded elsewhere
- attachment and generated-artifact persistence records metadata in
  `app.assets`, but the implementation still treats `storage_path` as a local
  filesystem path rather than a generic storage locator

This plan turns those requirements into one coherent application contract that
infra and deploy automation can consume later.

## Goals

- preserve the stable browser attachment contract:
  - upload via `POST /api/attachments`
  - read via `GET /attachments/{attachment_id}`
- keep durable attachment metadata free of presigned URLs
- introduce typed storage locator semantics so local development and deployed
  object storage can share the same attachment abstraction
- add deterministic helper logic for deployed product-image public URLs on the
  same app hostname
- keep scope app-side:
  - backend code
  - config
  - bootstrap helpers
  - tests
  - deploy/runtime docs

## Non-Goals

- no Terraform, S3 bucket policy, CloudFront distribution, IAM, or release
  workflow changes
- no direct browser-to-S3 upload flow
- no user-auth or per-user attachment authorization changes
- no attempt to remove local backend-proxy product-image routes used by local
  development and tests

## Core Decisions

### 1. Treat `storage_path` as a storage locator

`app.assets.storage_path` remains the existing durable column name for v1, but
the application should stop assuming it is always a filesystem path.

The app contract becomes:

- local development may still use disk-backed locators
- deployed environments may persist private object keys or bucket-relative
  locators
- attachment reads resolve the locator through a storage backend instead of
  opening `Path(storage_path)` directly

### 2. Keep app-proxied attachment reads

The stable browser route remains `/attachments/{attachment_id}`.

For this slice, reads should continue to proxy or stream bytes back through the
backend route so the UI contract stays unchanged and durable state never needs
to expose presigned URLs.

### 3. Make product-image public URLs deterministic

`direct_public_url` mode should not depend on hand-written `public_url` values.

The app/bootstrap layer should be able to compute the deployed URL from:

- the configured same-host product-image base URL
- the image run id
- a stable image key per catalog row

That keeps seeding repeatable and aligned with the deployment spec.

## Deliverables

- typed attachment storage backend abstraction in `src/ikea_agent/chat_app/`
- runtime wiring that resolves persisted attachment locators through that
  abstraction
- bootstrap helper(s) for deterministic product-image `public_url` seeding
- focused tests covering:
  - stable attachment URIs
  - durable non-presigned locators
  - deterministic product-image public URLs
- deploy/runtime docs updated to describe the concrete contract

## Validation

- targeted pytest coverage for attachment storage and product-image URL helpers
- any related route-level tests needed for attachment reads
- `make tidy`
