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

## Legacy Content

Historical plans/specs/SQL and pre-simplification modules are in `legacy/`.
They are reference-only and are intentionally excluded from active implementation guidance.

## Quality

- `make format-all`
- `make test`
- `make tidy`
