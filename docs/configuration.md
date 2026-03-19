# Configuration

Runtime config is defined in `src/ikea_agent/config.py` and loaded from `.env`.

## Core Settings

- `DATABASE_URL` default: `postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent`
- `EMBEDDING_MODEL_URI` default: `google-gla:gemini-embedding-001`
- `EMBEDDING_DIMENSIONS` default: `256` (fixed to match the current pgvector column shape)
- `GEMINI_GENERATION_MODEL` default: `gemini-3.1-flash-lite-preview`
- `ALLOW_MODEL_REQUESTS` default: `1`
- `MMR_LAMBDA` default: `0.8`
- `MMR_PRESELECT_LIMIT` default: `30`
- `EMBEDDING_NEIGHBOR_LIMIT` default: `0` (legacy/precompute-only knob; active Postgres diversification ignores it)
- `IMAGE_SERVING_STRATEGY` default: `backend_proxy`
- `IMAGE_SERVICE_BASE_URL` default: unset
- `IKEA_IMAGE_CATALOG_RUN_ID` default: unset

## Notes

- Embeddings are generated via pydantic-ai embedding providers.
- Active local runtime expects a pgvector-enabled Postgres for both relational data and semantic
  retrieval.
- `catalog.*` holds seeded product metadata, embeddings, image metadata, and optional precomputed
  embedding neighbors; `app.*` remains the runtime schema for conversation and analysis tables.
- `ops.seed_state` records the current local Postgres and image-catalog seed versions.
- Worktree bootstrap writes `DATABASE_URL` into `.tmp_untracked/worktree.env` and uses
  `scripts/worktree/deps.sh` to ensure the slot-local Postgres service.
- Normal `ensure-postgres` and bootstrap flows now restore the latest versioned snapshot from
  `<CANONICAL_ROOT>/.tmp_untracked/docker-deps/snapshots/latest.json` instead of reseeding from
  canonical parquet and image inputs.
- `scripts/worktree/deps.sh reseed --slot <n>` remains the explicit rebuild-from-source
  maintenance path.
- Operational dependency-prep tooling now lives under `scripts/docker_deps/`, not under the
  application package.
- Use `uv run python -m scripts.docker_deps.seed_postgres` to seed Postgres from canonical
  parquet and image-catalog inputs.

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
