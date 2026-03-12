# Current Search Data Access

This document captures how the active search pipeline accesses data today.

## Search Pipeline Path

The active orchestration in `src/ikea_agent/chat/search_pipeline.py` runs:

1. Build `RetrievalRequest` from user query + filters.
2. Embed query text via runtime embedder (`chat/runtime.py`).
3. Search Milvus Lite vectors and hydrate candidates from DuckDB.
4. Rerank candidates.
5. Apply MMR diversification.
6. Return `SearchGraphToolResult` for tool/UI rendering.

## Retrieval Data Path

`run_search_pipeline_batch` uses runtime helpers in `chat/runtime.py`:

1. Embed query text through `pydantic_ai.Embedder`.
2. Search Milvus Lite collection for nearest vectors.
3. Hydrate candidate keys in DuckDB (`app.products_canonical` + `app.product_embeddings`).
4. Apply structured filters in inline SQL.

## Raw Data vs Embeddings

- Raw product metadata: DuckDB `app.products_canonical`.
- Embedding vectors at runtime: Milvus Lite collection.
- Embedding source-of-truth snapshots: DuckDB `app.product_embeddings` and parquet artifacts in `data/parquet/`.

## Legacy State Clarification

- Old graph-orchestrated retrieval is removed from active runtime.
- Old SQL-file-driven retrieval pipeline is archived under `legacy/sql/`.
- Active runtime does not import from `legacy/` modules.
