# Data Model and Schema

## Sources
- Initial source: IKEA CSV (`data/IKEA_product_catalog.csv`)
- Raw source rows are staged in `app.products_raw`

## Canonical Tables
Defined in `sql/10_schema.sql` and modeling SQL:

- `app.products_raw`
  - Flat source columns from CSV, including `unique_id`, `product_id`, categories, dimensions, price, currency, and `country`
- `app.products_canonical`
  - Germany-scoped canonical rows keyed by `canonical_product_key`
  - Parsed numeric fields: `width_cm`, `depth_cm`, `height_cm`, `price_eur`
- `app.product_alias_map`
  - Alias links from raw identifiers to canonical keys
- `app.product_family_map`
  - Family grouping by normalized product name + type

## Embedding and Retrieval Tables
- `app.embedding_runs`
  - Run metadata for indexing job status and throughput
- `app.product_embeddings`
  - Embedding vectors per canonical key, model, and strategy version
- `app.query_log`
  - Retrieval request logs with filter values, latency, and low-confidence flag
- `app.shortlist_global`
  - Global persisted shortlist entries

## Evaluation Tables
- `app.eval_prompt_registry`
- `app.eval_subset_registry`
- `app.eval_queries_generated`
- `app.eval_labels`
- `app.eval_runs`

## SQL-First Policy
- All schema/load/query logic is under `sql/`.
- Python orchestration calls SQL files and avoids inline complex SQL.

## Documentation Rule
Any schema or semantic change must update this page in the same change.
