# ikea_agent

Simplified IKEA search/runtime project centered on:

- `pydantic-ai` for agent runtime
- `pydantic-graph` for orchestration
- Milvus Lite for vector similarity
- DuckDB for simple typed metadata access

## Quickstart

1. Install dependencies:
   - `make deps`
2. Run preflight:
   - `make preflight`
3. Run chat runtime:
   - `make chat`
4. Open:
   - `http://127.0.0.1:8000`

## Active Runtime Layout

- `src/ikea_agent/chat/` graph + agent wiring
- `src/ikea_agent/chat_app/` FastAPI app entrypoint
- `src/ikea_agent/retrieval/` Milvus + DuckDB data access
- `src/ikea_agent/shared/` typed contracts and DB bootstrap helpers

## Phase 2 Highlights
- Single strategy-free embedding pipeline (`app.embedding_input`).
- Multi-country description rollup table: `app.product_description_country_rollup`.
- Local parquet artifacts exported under `data/parquet/`.
- Search UX includes sort modes, advanced filters, reset, and active-filter chips.
- Typed floor-planner tooling under `src/tal_maria_ikea/tools/` for agent-compatible room visualization.

## Legacy Content

Historical plans/specs/SQL and pre-simplification modules are in `legacy/`.
They are reference-only and are intentionally excluded from active implementation guidance.

## Quality

- `make format-all`
- `make test`
- `make tidy`
