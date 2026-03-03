# Planned Pipeline (Scaffold)

## Overview
1. Load and normalize IKEA catalog records
2. Generate embeddings with Gemini
3. Persist vectors and metadata in DuckDB
4. Fetch candidates and rerank with Hugging Face model

## Typed Boundaries
Defined in `src/tal_maria_ikea/types.py`:
- `CatalogLoader`
- `EmbeddingGenerator`
- `VectorStore`
- `Reranker`

## Failure Points to Handle in Implementation
- Missing/invalid source rows during normalization
- Embedding API request failures and retries
- Vector persistence conflicts
- Reranker model load latency and memory pressure (M1/MPS considerations)

This file is design-only until feature work begins.
