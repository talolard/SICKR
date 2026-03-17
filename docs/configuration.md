# Configuration

Runtime config is defined in `src/ikea_agent/config.py` and loaded from `.env`.

## Core Settings

- `DUCKDB_PATH` default: `data/ikea.duckdb`
- `MILVUS_LITE_URI` default: `data/milvus_lite.db`
- `MILVUS_COLLECTION` default: `ikea_product_embeddings`
- `EMBEDDING_MODEL_URI` default: `google-gla:gemini-embedding-001`
- `EMBEDDING_DIMENSIONS` default: `256`
- `GEMINI_GENERATION_MODEL` default: `gemini-3.1-flash-lite-preview`
- `ALLOW_MODEL_REQUESTS` default: `1`
- `MMR_LAMBDA` default: `0.8`
- `MMR_PRESELECT_LIMIT` default: `30`
- `EMBEDDING_NEIGHBOR_LIMIT` default: `0` (`0` means store all pairwise neighbors)

## Notes

- Embeddings are generated via pydantic-ai embedding providers.
- Milvus Lite stores vectors; DuckDB stores product metadata and embedding snapshots.
- Use `uv run python -m ingest.hydrate_milvus` to load/rebuild Milvus from DuckDB snapshots and
  recompute `app.product_embedding_neighbors` in batch.

## Agent Model Overrides

Agents resolve generation models with this precedence:

1. Explicit runtime override passed by caller.
2. Per-agent config in `agents` (legacy alias: `subagents`).
3. Global `GEMINI_GENERATION_MODEL`.

The search agent uses this same precedence now and no longer carries a separate
hardcoded fallback model.

Backend tests still force model requests off regardless of app defaults by using
Pydantic AI's `override_allow_model_requests(False)` autouse fixture in
[`tests/conftest.py`](../tests/conftest.py).

Environment example for one override:

```bash
AGENTS__FLOOR_PLAN_INTAKE__MODEL=gemini-3.1-flash
```
