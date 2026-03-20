# Current Search Data Access

This document captures how the active search pipeline accesses data today.

## Search Pipeline Path

The active orchestration in `src/ikea_agent/chat/search_pipeline.py` runs:

1. Build `RetrievalRequest` from user query + filters.
2. Embed query text via runtime embedder (`chat/runtime.py`).
3. Search Postgres `catalog.product_embeddings` directly with pgvector and hydrate typed catalog rows in the same repository query.
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
2. Run one SQLAlchemy-built pgvector query against `catalog.product_embeddings` joined with
   `catalog.products_canonical`.
3. Apply structured filters, sorting, and limits inside that repository query.

## Raw Data vs Embeddings

- Raw product metadata: Postgres `catalog.products_canonical`.
- Embedding vectors at runtime: Postgres `catalog.product_embeddings` with pgvector.
- Embedding source-of-truth snapshots: Postgres `catalog.product_embeddings`, plus canonical parquet
  artifacts in `data/parquet/`.
- Neighbor similarities: Postgres computes pairwise candidate-set similarities directly from
  `catalog.product_embeddings` with pgvector distance expressions; `catalog.product_embedding_neighbors`
  is now an optional legacy surface only.

## Legacy State Clarification

- Old graph-orchestrated retrieval is removed from active runtime.
- Old SQL-file-driven retrieval pipeline is archived under `legacy/sql/`.
- Active runtime does not import from `legacy/` modules.
