# Web App Runbook

## Start
1. Initialize and load DB:
   - `./scripts/init_duckdb.sh`
   - `./scripts/load_ikea_data.sh`
2. Build embeddings:
   - `uv run python -m tal_maria_ikea.ingest.index`
3. Run Django app:
   - `uv run python -m tal_maria_ikea.web.runserver --host 127.0.0.1 --port 8000`

## Routes
- `/` search page (query + filters + results + shortlist)
- `/admin/` Django admin for Phase 3 config entities
- `/analysis/rerank-diff/<request_id>` before/after rank comparison view
- `POST /shortlist/add` add one item to global shortlist
- `POST /shortlist/remove` remove one item from global shortlist

## Admin-Managed Config Models (SQLite)

These entities are managed in Django admin and used as Phase 3 control/config plane:

- `SystemPromptTemplate`
  - Versioned system-prompt templates with required `{{ user_query }}` placeholder.
- `PromptVariantSet`
  - Named groups of templates for prompt-comparison runs.
- `FeedbackReasonTag`
  - Allowed reason tags by scope (`turn`/`item`) and polarity (`up`/`down`).
- `ExpansionPolicyConfig`
  - Query expansion heuristic thresholds and feature toggles.

## Search Filters
- Category
- Sort (`relevance`, `price_asc`, `price_desc`, `size`)
- EUR price range (`min_price_eur`, `max_price_eur`)
- Dimensions in collapsed advanced controls (exact/min/max per width/depth/height in cm)
- Active filter chips and reset action

## Shortlist Behavior
- Persistence table: `app.shortlist_global`
- Scope: global (no auth/session split)
- Duplicate adds: de-duplicated by `canonical_product_key` via upsert

## Debugging
- Query logs: `app.query_log`
- Query logs include `sort_mode` for behavior analysis.
- Low-confidence banner is based on top semantic score threshold from settings.
