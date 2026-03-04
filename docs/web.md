# Web App Runbook

## Start
1. Initialize and load DB:
   - `./scripts/init_duckdb.sh`
   - `./scripts/load_ikea_data.sh`
2. Build embeddings:
   - `uv run python -m tal_maria_ikea.ingest.index`
3. Run chat app:
   - `uv run python -m tal_maria_ikea.chat_app.runserver --host 127.0.0.1 --port 8000`

## Routes
- `GET /healthz` runtime health probe
- `POST /api/chat/run` typed chat execution endpoint
- `GET /api/chat/trace/<request_id>` minimal persisted trace view
- `GET /chat` pydantic-ai web chat UI

## Config Plane (DuckDB)

Phase 3 runtime config now lives in DuckDB tables seeded by `sql/43_chat_config.sql`:

- `app.system_prompt_template_config`
- `app.prompt_variant_set_config`
- `app.prompt_variant_set_template_link`
- `app.feedback_reason_tag_config`
- `app.expansion_policy_config`

## Runtime Behavior
- Chat executes one graph run per user turn:
  - parse -> expand -> retrieve -> rerank -> summarize -> refine -> persist -> respond
- Retrieval snapshots and conversation messages persist via `app.search_*` and `app.conversation_*` tables.
