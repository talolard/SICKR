# Web App Runbook

## Start
1. Initialize and load DB:
   - `./scripts/init_duckdb.sh`
   - `./scripts/load_ikea_data.sh`
2. Build embeddings:
   - `uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first`
3. Run Django app:
   - `uv run python -m tal_maria_ikea.web.runserver --host 127.0.0.1 --port 8000`

## Routes
- `/` search page (query + filters + results + shortlist)
- `POST /shortlist/add` add one item to global shortlist
- `POST /shortlist/remove` remove one item from global shortlist

## Search Filters
- Category
- EUR price range (`min_price_eur`, `max_price_eur`)
- Dimensions (exact/min/max per width/depth/height in cm)

## Shortlist Behavior
- Persistence table: `app.shortlist_global`
- Scope: global (no auth/session split)
- Duplicate adds: de-duplicated by `canonical_product_key` via upsert

## Debugging
- Query logs: `app.query_log`
- Low-confidence banner is based on top semantic score threshold from settings.
