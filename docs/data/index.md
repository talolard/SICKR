# Data Model and Schema

## Sources
- Initial source: IKEA CSV (`data/IKEA_product_catalog.csv`)
- Raw payload is staged in `app.products_raw`

## DuckDB Tables
Defined in `sql/10_schema.sql`:
- `app.products_raw`
  - `source_row_id` (BIGINT)
  - `payload` (JSON)
  - `ingested_at` (TIMESTAMP)
- `app.products`
  - `product_id` (VARCHAR, PK)
  - `product_name` (VARCHAR)
  - `category` (VARCHAR)
  - `description` (VARCHAR)
  - `dimensions_text` (VARCHAR)
  - `price_text` (VARCHAR)
  - `currency` (VARCHAR)
  - `created_at`, `updated_at` (TIMESTAMP)
- `app.product_embeddings`
  - `product_id` (VARCHAR, PK)
  - `embedding_model` (VARCHAR)
  - `embedding_json` (JSON)
  - `embedded_at` (TIMESTAMP)
- `app.query_log`
  - `query_id` (VARCHAR, PK)
  - `query_text` (VARCHAR)
  - `query_limit` (INTEGER)
  - `request_source` (VARCHAR)
  - `created_at` (TIMESTAMP)

## SQL-First Policy
- All schema/load/query logic is stored under `sql/`.
- Python should call SQL files, not construct long inline SQL, unless strongly justified.

## Raw CSV Retention
After successful load, the raw CSV may be removed (`DELETE_RAW=1 ./scripts/load_ikea_data.sh`).
A spare copy should be kept outside this repository.

## Documentation Change Rule
Any schema or semantic change requires updating this page in the same change.
