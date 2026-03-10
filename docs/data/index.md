# Data Model and Storage

## Active Runtime Stores

### DuckDB (`data/ikea.duckdb`)

Active runtime uses DuckDB for:
- `app.products_canonical` (catalog metadata)
- `app.product_embeddings` (embedding snapshot source used to build Milvus)
- `app.product_embedding_neighbors` (precomputed cosine neighbors used by MMR diversification)

### Milvus Lite (`data/milvus_lite.db`)

Active runtime uses Milvus Lite collection:
- `ikea_product_embeddings` (configurable)
- stores vector records used for semantic candidate retrieval

## Migrations

- Runtime schema migrations use Alembic + SQLAlchemy.
- See [Runtime DB Migrations](migrations.md) for commands and environment overrides.

## Data Lifecycle

1. Embedding snapshots live in DuckDB/parquet data artifacts.
2. Ingest hydrates Milvus Lite from DuckDB embeddings.
3. Ingest precomputes top-k embedding neighbors and stores them in DuckDB.
4. Query flow retrieves vector candidates from Milvus.
5. DuckDB hydrates/filter candidates and provides neighbor similarities for MMR.

## Tool Sample Inputs
- Floor planner sample inputs live in typed tests under `tests/tools/test_floor_planner_*.py`.
- Inputs are modeled as centimeter-based Pydantic payloads.
- Generated floor-plan PNGs are runtime artifacts only and are not stored in git.

## Phase 2 References
- `spec/phase2/source_notes.md`
- `spec/phase2/ui_critique.md`

## Legacy

Historical SQL-driven schema/modeling artifacts are archived in `legacy/sql/`.
