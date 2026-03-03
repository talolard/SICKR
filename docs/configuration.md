# Configuration Management

## Goals
Keep configuration explicit, typed, and environment-driven while preventing secret leakage.

## Canonical Key Registry
The current required/expected keys are:

- `GCP_PROJECT_ID` (required)
- `GCP_REGION` (default `us-central1`)
- `GEMINI_MODEL` (default `text-embedding-004`)
- `GOOGLE_APPLICATION_CREDENTIALS` (required for local credentialed runs)
- `IKEA_RAW_CSV_PATH` (default `data/IKEA_product_catalog.csv`)
- `DUCKDB_PATH` (default `data/ikea.duckdb`)
- `LOG_LEVEL` (default `INFO`)
- `LOG_JSON` (default `true`)
- `APP_ENV` (default `dev`)
- `DEFAULT_QUERY_LIMIT` (default `25`)

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
