# Configuration

Runtime config is defined in `src/ikea_agent/config.py` and loaded from `.env`.

## Core Settings

- `DUCKDB_PATH` default: `data/ikea.duckdb`
- `MILVUS_LITE_URI` default: `data/milvus_lite.db`
- `MILVUS_COLLECTION` default: `ikea_product_embeddings`
- `MILVUS_REBUILD_ON_START` default: `false`
- `EMBEDDING_MODEL_URI` default: `google-gla:gemini-embedding-001`
- `EMBEDDING_DIMENSIONS` default: `256`
- `GEMINI_GENERATION_MODEL` default: `gemini-3.1-flash-lite-preview`

## Notes

- Embeddings are generated via pydantic-ai embedding providers.
- Milvus Lite stores vectors; DuckDB stores product metadata and query logs.
