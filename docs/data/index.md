# Data Model and Storage

## Active Runtime Stores

### DuckDB (`data/ikea.duckdb`)

Active runtime uses DuckDB for:
- `app.products_canonical` (catalog metadata)
- `app.product_embeddings` (embedding snapshot source used to build Milvus)

### Milvus Lite (`data/milvus_lite.db`)

Active runtime uses Milvus Lite collection:
- `ikea_product_embeddings` (configurable)
- stores vector records used for semantic candidate retrieval

## Data Lifecycle

1. Embedding snapshots live in DuckDB/parquet data artifacts.
2. A dedicated ingest script loads Milvus Lite from DuckDB embeddings.
3. Query flow retrieves vector candidates from Milvus.
4. DuckDB hydrates and filters candidate products.

## Legacy

Historical SQL-driven schema/modeling artifacts are archived in `legacy/sql/`.
