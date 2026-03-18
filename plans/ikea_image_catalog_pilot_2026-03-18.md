# IKEA Image Catalog Pilot

## Summary

Build a Scrapy-based sidecar at `sidecars/ikea_image_catalog/` that:

- samples product-page inputs from `data/parquet/products_raw`
- discovers product-only image URLs from IKEA product pages
- downloads deduplicated master assets
- writes JSONL and Parquet catalogs plus a run summary under `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog/`

## Design

- Product identity uses raw `product_id`; repo `canonical_product_key` is nullable enrichment only.
- Discovery is page-based and emits one row per `(product_id, image_asset_key)`.
- Download is asset-based and emits one row per `image_asset_key`.
- Final `catalog.jsonl` merges discovery rows with download rows.

## Extraction Rules

Keep:

- hydrated image objects whose `type` ends with `_PRODUCT_IMAGE`
- product JSON-LD `ImageObject.contentUrl`
- `og:image` as fallback and sanity flag

Exclude:

- recommendation carousels
- promo/category `imageUrl` fields
- `nowAtIkeaCategoryImage`
- room inspiration and `ingkadam` imagery
- header/footer/global assets

## Output Contract

- Shared output root:
  - `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog/`
- Per-run files:
  - `runs/<run_id>/seed_products.jsonl`
  - `runs/<run_id>/discovered.jsonl`
  - `runs/<run_id>/download_manifest.jsonl`
  - `runs/<run_id>/downloads.jsonl`
  - `runs/<run_id>/catalog.jsonl`
  - `runs/<run_id>/catalog.parquet`
  - `runs/<run_id>/run_summary.json`
- Shared master images:
  - `images/masters/<image_asset_key>`

## JSONL Schema

Each final catalog row includes:

- product fields: `product_id`, `repo_canonical_product_key`, `product_name`, `country`
- page fields: `source_page_url`, `page_fetch_url`, `page_canonical_url`, `page_article_number`, `page_title`, `page_product_name`, `page_og_image_url`, `page_gallery_image_count`, `page_http_status`
- image fields: `image_asset_key`, `canonical_image_url`, `variant_urls`, `variant_query_codes`, `image_rank`, `image_role`, `is_og_image`, `extraction_source`, `extraction_warnings`
- download fields: `download_status`, `download_http_status`, `content_type`, `content_length_bytes`, `etag`, `cache_control`, `sha256`, `width_px`, `height_px`, `image_format`, `color_mode`, `files_pipeline_checksum`, `local_path`, `storage_uri`, `downloaded_at`
- process fields: `crawl_run_id`, `scraped_at`, `asset_key_conflict`

## Validation

- Sidecar tests run from the sidecar project:
  - `uv run --project sidecars/ikea_image_catalog pytest`
- Repo gate still runs from the main project:
  - `make tidy`

## Pilot Findings

Pilot run `pilot-1000` completed on March 18, 2026.

- Seeds: 1,000 product pages
- Discovery rows: 5,118
- Unique canonical assets: 5,045
- Cached local assets reused: 27
- Newly downloaded assets: 5,018
- Failed asset downloads: 0
- Discovery response statuses: `200=1000`, `301=7`
- Asset download response statuses: `200=5018`
- Discovery elapsed time: about 308 seconds
- Download elapsed time: about 1,547 seconds
- Total downloaded bytes in this run: 1,171,991,792
- Shared master-image store size after the run: 1,178,368,708 bytes across
  5,045 files

Notes:

- The discovery phase was fast relative to the download phase. The current
  conservative throttling produced a stable baseline of roughly 195 asset
  downloads per minute.
- Live pages in this sample were fully covered by Product JSON-LD. Hydrated
  product-image objects were absent, so every catalog row carried
  `hydration_product_images_missing`.

## Pilot Progress

Partial pilot status as of 2026-03-18:

- `pilot-1000-20260318b` completed discovery for 1,000 sampled product pages
- discovery yielded 5,118 product-image rows
- dedupe reduced the download stage to 4,917 canonical assets
- the run was interrupted intentionally after 981 downloaded assets and about
  260.66 MB stored in `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog/images/masters/`

Blocker:

- the observed average asset size projects the full pilot above 1 GB of local
  downloads, so completion is waiting on explicit user approval per `AGENTS.md`
- Scrapy job state is preserved under
  `runs/pilot-1000-20260318b/jobdir-download/`, so the pilot can resume with
  the same run id
