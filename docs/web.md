# Web App Runbook

## Start

1. Install dependencies:
   - `make deps`
2. Run preflight checks:
   - `make preflight`
3. Run chat app:
   - `make chat`

## Runtime Shape

- FastAPI app mounts pydantic-ai web UI.
- Chat graph flow is parse -> retrieve -> rerank -> return.
- Retrieval uses Milvus Lite for semantic candidates and DuckDB for metadata hydration.

## Routes

- `GET /` pydantic-ai web chat UI
