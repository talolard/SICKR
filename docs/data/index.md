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

## Tool Sample Fixtures
- Floor planner sample inputs live in `tests/fixtures/floor_planner/`.
- They include valid non-rectangular and hallway layouts, plus invalid geometry cases.
- Generated floor-plan PNGs are runtime artifacts only and are not stored in git.

## Phase 2 References
- `spec/phase2/source_notes.md`
- `spec/phase2/ui_critique.md`

## Legacy

Historical SQL-driven schema/modeling artifacts are archived in `legacy/sql/`.
