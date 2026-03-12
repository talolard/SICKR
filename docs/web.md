# Web App Runbook

## Start

1. Install dependencies:
   - `make deps`
2. Run preflight checks:
   - `make preflight`
3. Run chat app:
   - `make chat`

## UI Commands

- Start UI against the real backend: `make ui-dev-real`
- Start UI against the mock backend: `make ui-dev-mock`
- Run UI unit tests: `make ui-test`
- Run UI mock E2E: `make ui-test-e2e`
- Run real-backend UI smoke: `make ui-test-e2e-real-ui-smoke`

## Runtime Shape

- FastAPI app builds shared runtime dependencies, serves support APIs, mounts per-agent pydantic-ai web UIs, and exposes AG-UI POST handlers.
- Chat request flow is parse request -> selected `pydantic_ai.Agent` -> tool call(s) -> streamed response.
- Retrieval uses Milvus Lite for semantic candidates and DuckDB for metadata hydration.

## Routes

- `GET /api/agents` returns registered agent metadata for the UI
- `POST /ag-ui/agents/{agent_name}` runs one named agent through the AG-UI transport
- `GET /agents/{agent_name}/chat/` serves the mounted pydantic-ai web chat UI for one agent
- `POST /attachments` uploads one image attachment for later tool use
