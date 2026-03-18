# Local Product Images

The search runtime can serve locally cataloged IKEA product images from the
shared sidecar output root:

- `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`

## Runtime Contract

- Startup builds an in-memory index from completed run outputs under `runs/`.
- Each run prefers `catalog.parquet` when present and falls back to `catalog.jsonl`.
- Rows without a valid `local_path` on disk are ignored.
- Image ranking prefers `is_og_image`, then `image_rank`, then canonical URL.

## UI Contract

- Search results and bundle detail cards receive `image_urls` directly in the
  tool payloads.
- Missing images render a placeholder tile instead of triggering extra fetches.
- The backend serves image bytes from:
  - `/static/product-images/{product_id}`
  - `/static/product-images/{product_id}/{ordinal}`

## Identity

- Agent payloads still use the existing canonical product key.
- The backend derives raw `product_id` by splitting the canonical key on the
  last `-`, for example `28508-DE -> 28508`.
