# IKEA Image Catalog Sidecar

## Purpose

This sidecar builds a local catalog of product-only IKEA images so the app can
display them later without scraping at render time.

## Why It Exists

IKEA product pages mix product-gallery images with unrelated assets such as
recommendations, category graphics, and room imagery. The sidecar extracts only
product images, downloads deduplicated master assets, and writes reusable JSONL
and Parquet catalogs for later UI wiring.

## Run It

```bash
uv run --project sidecars/ikea_image_catalog \
  python -m ikea_image_catalog.cli crawl \
  --limit 1000 \
  --run-id pilot-1000
```

Optional:

- `--country Germany --country USA` to constrain the sample
- `--output-root /some/other/path` to override the default shared output root

## Output Root

Default output root:

`/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog/`

This is intentionally shared across worktrees so pilot runs and downloaded
master images live in one stable location.

## Files Produced

- `runs/<run_id>/seed_products.jsonl`
- `runs/<run_id>/discovered.jsonl`
- `runs/<run_id>/download_manifest.jsonl`
- `runs/<run_id>/downloads.jsonl`
- `runs/<run_id>/catalog.jsonl`
- `runs/<run_id>/catalog.parquet`
- `runs/<run_id>/run_summary.json`
- `images/masters/<image_asset_key>`

## Extraction Policy

Kept signals:

- hydrated product image objects whose `type` ends with `_PRODUCT_IMAGE`
- product JSON-LD `ImageObject.contentUrl`
- `og:image` as a fallback/sanity signal

Explicitly excluded:

- recommendation carousels
- promo/category `imageUrl` fields
- `nowAtIkeaCategoryImage`
- room inspiration images
- header/footer/global assets

## Catalog Notes

- Product identity uses raw `product_id`.
- `repo_canonical_product_key` is nullable enrichment only.
- `image_asset_key` is the locale-agnostic product image path after
  `/images/products/`, with query stripped.
- `canonical_image_url` is the master URL without `?f=...`.
- `variant_urls` records observed page-local size variants for the same product
  image.
- Stage two uses Scrapy `FilesPipeline`, so downloaded rows also capture the
  pipeline checksum alongside HTTP and image metadata.

## Pilot Findings

Pilot run `pilot-1000` completed on March 18, 2026 under the shared output root.

- 1,000 sampled product pages produced 5,118 catalog rows and 5,045 unique
  canonical assets.
- 27 assets were already present in the shared local cache, so the run
  downloaded 5,018 new master images and had 0 failed asset downloads.
- Discovery finished in about 5.1 minutes; the asset download stage took about
  25.8 minutes. End-to-end runtime was about 30.9 minutes with the current
  conservative throttling.
- Discovery responses were 1,000 `200`s and 7 `301`s. Asset downloads were
  5,018 `200`s with no observed 4xx/5xx responses in the final asset records.
- The downloaded payload total was 1,171,991,792 bytes, about 1.17 GB. The
  deduplicated shared image store held 5,045 master files using 1,178,368,708
  bytes after the pilot.
- In this live sample, extraction was fully covered by Product JSON-LD. The
  catalog rows all carried `hydration_product_images_missing`, so hydrated
  product-image objects were not present in the current fetched markup even
  though the extractor still supports them for known fixture shapes.
- `catalog.jsonl` is the source of truth. `catalog.parquet` is a convenience
  export for downstream analysis.

## Pilot Status

Current pilot run:

- `run_id=pilot-1000-20260318b`
- discovery completed for 1,000 sampled product pages
- discovery produced 5,118 product-image rows and 4,917 canonical download rows
- the download stage was paused intentionally after 981 downloaded assets and
  about 260.66 MB written under `images/masters/`

Why it is paused:

- the observed average asset size projects the full download stage above 1 GB
  of local downloads
- `AGENTS.md` says to confirm before doing that on this machine

Resume behavior:

- the sidecar uses Scrapy `JOBDIR` state per run
- rerunning the same command with `--run-id pilot-1000-20260318b` can resume the
  interrupted download stage once the download-size decision is made
