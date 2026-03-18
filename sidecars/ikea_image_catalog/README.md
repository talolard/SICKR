# IKEA Image Catalog Sidecar

Scrapy-based sidecar for discovering product-only IKEA images, downloading the
master assets, and writing JSONL plus Parquet catalogs for later app use.

Primary entrypoint:

```bash
uv run --project sidecars/ikea_image_catalog \
  python -m ikea_image_catalog.cli crawl \
  --limit 1000 \
  --run-id pilot-1000
```

For the full incremental crawl, use:

```bash
uv run --project sidecars/ikea_image_catalog \
  python -m ikea_image_catalog.cli crawl \
  --all \
  --run-id all-products-20260318 \
  --concurrent-requests 16 \
  --concurrent-requests-per-domain 8 \
  --autothrottle-target-concurrency 4
```

This reuses the shared image cache and, by default, skips product-page URLs that
already appear in prior `discovered.jsonl` outputs under the shared output root.

`catalog.jsonl` is the source of truth. `catalog.parquet` is a convenience
export produced locally from the JSONL catalog.
