# Current Search Data Access

This document captures how the active search pipeline accesses data today.

## Search Pipeline Path

The active orchestration in `src/ikea_agent/chat/search_pipeline.py` runs:

1. Build `RetrievalRequest` from user query + filters.
2. Embed query text via runtime embedder (`chat/runtime.py`).
3. Search the shared Milvus collection and hydrate candidates from Postgres.
4. Rerank candidates with the configured backend.
5. Apply MMR diversification.
6. Return `SearchGraphToolResult` for tool/UI rendering.

Default reranking is lexical token overlap. The optional transformer backend is
explicitly opt-in via `RERANK_BACKEND=transformer` and requires local `torch`
plus `transformers` dependencies; otherwise runtime construction fails fast and
deployments should stay on the lexical backend.

## Retrieval Data Path

`run_search_pipeline_batch` uses runtime helpers in `chat/runtime.py`:

1. Embed query text through `pydantic_ai.Embedder`.
2. Search the shared Milvus collection for nearest vectors.
3. Hydrate candidate keys in Postgres (`catalog.products_canonical` + `catalog.product_embeddings`).
4. Apply structured filters in inline SQL.

## Raw Data vs Embeddings

- Raw product metadata: Postgres `catalog.products_canonical`.
- Embedding vectors at runtime: shared Milvus collection.
- Embedding source-of-truth snapshots: Postgres `catalog.product_embeddings`, plus canonical parquet
  artifacts in `data/parquet/`.
- Neighbor similarities: Postgres `catalog.product_embedding_neighbors` when seeded; otherwise the
  repository computes cosine similarities from stored embeddings on demand.

## Legacy State Clarification

- Old graph-orchestrated retrieval is removed from active runtime.
- Old SQL-file-driven retrieval pipeline is archived under `legacy/sql/`.
- Active runtime does not import from `legacy/` modules.
