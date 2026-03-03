# tal_maria_ikea

Phase 1 semantic-search implementation for IKEA catalog exploration.

## Quickstart
1. Create `.env` from `.env.example` and set GCP credentials.
2. Initialize + load DB:
   - `./scripts/init_duckdb.sh`
   - `./scripts/load_ikea_data.sh`
3. Build embeddings:
   - `uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first`
4. Start web app:
   - `uv run python -m tal_maria_ikea.web.runserver`

## Quality
- `make format-all`
- `make test`
