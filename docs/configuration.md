# Configuration Management

## Goals
Keep configuration explicit, typed, and environment-driven while preventing secret leakage.

## Canonical Key Registry
The current required/expected keys are:

- `GCP_PROJECT_ID` (default `gen-lang-client-0545732168`)
- `GCP_REGION` (default `us-central1`)
- `GEMINI_MODEL` (default `gemini-embedding-001`)
- `GEMINI_GENERATION_MODEL` (default `gemini-2.5-flash`)
- `EMBEDDING_PROVIDER` (default `vertex_gemini`)
- `GOOGLE_APPLICATION_CREDENTIALS` (required when not using API key mode)
- `GEMINI_API_KEY` (optional, enables direct Gemini Developer API mode)
- `IKEA_RAW_CSV_PATH` (default `data/IKEA_product_catalog.csv`)
- `DUCKDB_PATH` (default `data/ikea.duckdb`)
- `LOG_LEVEL` (default `INFO`)
- `LOG_JSON` (default `true`)
- `APP_ENV` (default `dev`)
- `DEFAULT_QUERY_LIMIT` (default `25`)
- `DEFAULT_MARKET` (default `Germany`)
- `EMBEDDING_PARALLELISM` (default `8`)
- `EMBEDDING_BATCH_SIZE` (default `16`)
- `EMBEDDING_DIMENSIONS` (default `256`)
- `EMBEDDING_REQUESTS_PER_MINUTE` (default `90`)
- `EMBEDDING_MAX_RETRIES` (default `5`)
- `EMBEDDING_RETRY_BASE_SECONDS` (default `2.0`)
- `EMBEDDING_RETRY_MAX_SECONDS` (default `90.0`)
- `EMBEDDING_RETRY_JITTER_SECONDS` (default `1.0`)
- `EMBEDDING_UPSERT_CHUNK_SIZE` (default `25`)
- `EVAL_GENERATION_BATCH_SIZE` (default `25`)
- `EVAL_GENERATION_PARALLELISM` (default `4`)
- `EVAL_GENERATION_MAX_ROUNDS` (default `8`)
- `VSS_BUILD_INDEX` (default `false`)
- `VSS_METRIC` (default `cosine`)
- `RETRIEVAL_LOW_CONFIDENCE_THRESHOLD` (default `0.15`)
- `DJANGO_SECRET_KEY` (default `dev-only-secret`)
- `DJANGO_DEBUG` (default `true`)
- `DJANGO_ALLOWED_HOSTS` (default `127.0.0.1,localhost`)

## Django DB Scope

Phase 3 keeps Django SQLite as a config/admin plane and DuckDB as retrieval/runtime analytics plane.

Current Django-managed entities include:

- prompt templates and prompt variant sets
- feedback reason tags
- query expansion policy config

## Layering Order
Configuration precedence (lowest to highest):
1. Code defaults in `AppSettings`
2. `.env` local file
3. Shell environment variables
4. CI-provided environment variables

## Secret Handling
- Never commit `.env` files.
- Keep only placeholders in `.env.example`.
- Rotate secrets if they are ever exposed in logs/history.

## Validation Policy
- `make preflight` fails fast when required keys/files are missing.
- New required config keys must be documented here and reflected in `.env.example`.
