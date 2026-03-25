# Local Product Images

The search runtime can serve locally cataloged IKEA product images from the
shared sidecar output root:

- `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`

## Runtime Contract

- Startup builds an in-memory index from seeded Postgres rows in `catalog.product_images`.
- Seed inputs still come from completed sidecar run outputs under `runs/`; the Postgres seed step
  prefers `catalog.parquet` when present and falls back to `catalog.jsonl`.
- Rows may point at local shared-root files, direct public URLs, or both.
- Backend-proxy serving only works for rows with a readable `local_path` on disk.
- Image ranking prefers `is_og_image`, then `image_rank`, then canonical URL.
- When `IMAGE_SERVICE_BASE_URL` is set during bootstrap, seeded `public_url`
  values should use the same-host deployment shape:
  - `https://designagent.talperry.com/static/product-images/masters/<image-asset-key>`
- In `direct_public_url` mode, runtime lookup prefers seeded `public_url`, then
  can derive the same deterministic same-host URL from `image_asset_key` when
  the row has not been backfilled yet.

## Deployment Boundary

- In deployed environments, the runtime does not need the local image catalog on
  the host once the database has been seeded.
- Uploading `images/masters/` to S3 and seeding `catalog.product_images.public_url`
  is an environment-bootstrap task, not a normal per-release deploy step.

## UI Contract

- Search results and bundle detail cards receive `image_urls` directly in the
  tool payloads.
- Missing images render a placeholder tile instead of triggering extra fetches.
- With `IMAGE_SERVING_STRATEGY=backend_proxy`, the backend serves image bytes from:
  - `/static/product-images/{product_id}`
  - `/static/product-images/{product_id}/{ordinal}`
- With `IMAGE_SERVING_STRATEGY=direct_public_url`, runtime payloads use the seeded `public_url`
  value directly and do not require backend-local file serving.

## Identity

- Agent payloads still use the existing canonical product key.
- The backend derives raw `product_id` by splitting the canonical key on the
  last `-`, for example `28508-DE -> 28508`.
