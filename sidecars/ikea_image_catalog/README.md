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

`catalog.jsonl` is the source of truth. `catalog.parquet` is a convenience
export produced locally from the JSONL catalog.
