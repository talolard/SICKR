# Data Artifacts

This folder contains static local data artifacts for the ikea_agent runtime.

## Git LFS

All parquet artifacts under `data/parquet/` are tracked via Git LFS.
Do not store large parquet snapshots as normal Git blobs.

## What the data is

- `data/parquet/products_raw/*`:
  country-partitioned raw IKEA catalog snapshots.
- `data/parquet/products_canonical/*`:
  canonicalized product rows used by runtime hydration.
- `data/parquet/product_embeddings`:
  embedding vectors keyed by canonical product and model.
- `data/parquet/product_description_country_rollup`:
  description rollups by product and country coverage.

## How it was created

Historical generation used DuckDB export steps from legacy SQL/bootstrap flows.
The historical SQL is archived under `legacy/sql/`.

## Restore and static-source policy

This project treats these parquet snapshots as static restoration sources.
If local DuckDB/Milvus state is missing, these artifacts are the canonical source to rebuild from.
