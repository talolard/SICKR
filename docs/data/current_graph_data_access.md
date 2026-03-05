# Current Graph Data Access

This document captures how the active pydantic-graph runtime accesses data today.

## Graph Path

The active graph nodes in `src/ikea_agent/chat/graph.py` run:

1. `ParseUserIntentNode`
2. `RetrieveCandidatesNode`
3. `RerankNode`
4. `ReturnAnswerNode`

## Retrieval Data Path

`RetrieveCandidatesNode` uses runtime helpers in `chat/runtime.py`:

1. Embed query text through `pydantic_ai.Embedder` directly.
2. Search Milvus Lite collection for nearest vectors.
3. Hydrate candidate keys in DuckDB (`app.products_canonical` + `app.product_embeddings`).
4. Apply structured filters in inline SQL.

## Raw Data vs Embeddings

- Raw product metadata: DuckDB `app.products_canonical`.
- Embedding vectors at runtime: Milvus Lite collection.
- Embedding source-of-truth snapshots: DuckDB `app.product_embeddings` and parquet artifacts in `data/parquet/`.

## Legacy State Clarification

- Old SQL-file-driven retrieval pipeline is archived under `legacy/sql/`.
- Old Django/phase planning documents and phase modules are archived under `legacy/`.
- Active runtime does not use `legacy/` modules.
