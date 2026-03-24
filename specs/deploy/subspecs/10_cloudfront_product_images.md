# CloudFront Product Images

This subspec covers only the public delivery path for static product images.

Read [00_context.md](./00_context.md) first for the shared goals and
high-level deployment decisions.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

In deployed environments, product images should come from a CloudFront-backed S3
origin, not from the backend proxy routes.

The UI should still receive image URLs in the existing `image_urls` payload
shape. The change is where those URLs point.

## Why This Is Separate

Product images have a very different access pattern from attachments:

- they are static
- they are cacheable
- they do not need private access control
- they do not need the backend on the hot path for every request

That makes them a good fit for CDN-backed direct public URLs.

For this project, this is not just an optimization.
It is a launch requirement because the product-image set is large enough that
shipping it inside a container image or serving it repeatedly through the
backend would be wasteful in both image size and runtime traffic.

## Public URL Shape

Use the same public app hostname for product images.

Example:

- app pages: `https://designagent.talperry.com/...`
- product images:
  `https://designagent.talperry.com/static/product-images/<object-key>`

Why use the same hostname:

- it keeps the browser story simple
- it avoids introducing extra CORS questions for normal image rendering
- it keeps the public URL shape easy to understand

## CloudFront Routing Shape

Recommended CloudFront behavior:

- default behavior routes normal app traffic to the app origin
- `/static/product-images/*` routes to the S3 image origin

For the image behavior:

- allow `GET` and `HEAD`
- do not forward cookies
- do not forward viewer auth state
- keep the cache key simple
- prefer no query strings in image URLs
- enable long-lived caching

Because these images do not update in place, the image path should be treated as
immutable.

## Cache Policy

The intended cache posture is aggressive:

- long TTLs
- immutable object naming
- no routine invalidation dependency

Operational rule:

- when an image ever changes, publish it under a new object key
- do not rely on overwriting an existing key and waiting for caches to expire

## App Wiring

The app already supports two image-serving modes.

Relevant current behavior:

- with `IMAGE_SERVING_STRATEGY=backend_proxy`, the app emits
  `/static/product-images/...` backend routes
- with `IMAGE_SERVING_STRATEGY=direct_public_url`, the app passes through the
  seeded `public_url` value directly

That means the deployed CloudFront image plan should use:

- `IMAGE_SERVING_STRATEGY=direct_public_url`

And should not require backend proxy image serving for normal deployed traffic.

## What Must Be Seeded

The critical data contract is `catalog.product_images.public_url`.

For deployed environments, that field must contain the full CloudFront-backed
image URL on the app hostname.

Example shape:

- `https://designagent.talperry.com/static/product-images/<catalog-run-id>/<stable-key>.jpg`

The exact object-key convention can be decided later, but it should be:

- stable
- deterministic
- safe for long-lived CDN caching

## Backend Behavior After This Change

The backend proxy image routes should stay in the codebase for:

- local development
- test coverage
- fallback behavior when `public_url` is missing

But the intended deployed happy path is direct public URLs from seeded catalog
data, not backend-served bytes.

## UI Impact

No UI rewrite is required.

The UI already consumes `image_urls` as plain URLs. As long as the catalog rows
contain the CloudFront-backed URLs, the UI will render them as normal images.

## What This Subspec Does Not Decide

This subspec intentionally does not decide:

- the exact S3 bucket policy
- whether the S3 origin is public or fronted with CloudFront access control
- the exact CloudFront distribution config outside this path behavior
- the exact object-key generation logic
- the exact seed job that writes `public_url`

Those are implementation details for later infra or data-prep specs.

## Summary

The deployed image plan is:

- keep the UI contract unchanged
- switch deployed product images to `direct_public_url`
- seed full same-host CloudFront URLs into `catalog.product_images.public_url`
- route `/static/product-images/*` to the S3 image origin
- cache those objects aggressively because they are immutable
- do not launch with backend-proxy image serving as the intended public path
