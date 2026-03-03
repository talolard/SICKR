# tal_maria_ikea

Phase 1 semantic-search implementation for IKEA catalog exploration.

## Quickstart

1. Create `.env` from `.env.example`.
2. Set at least one auth method:
   - API key mode: `GEMINI_API_KEY=...`
   - or Vertex mode: `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/key.json`
3. Install dependencies:
   - `make deps`
4. Initialize data + index:
   - `make init`
   - Note: `make init` resets `data/ikea.duckdb` (greenfield workflow).
   - `make init` also runs eval query generation (`phase1_de_v1` / `p1_v1`).
5. Start web app:
   - `make web`
6. Open:
   - `http://127.0.0.1:8000`

## Common Commands

- `make db-init` initialize DuckDB schema
- `make db-load` load and model catalog data
- `make index` run embedding index pipeline
- `make vss-index` create HNSW index (DuckDB vss)
- `make eval` run eval metrics (requires generated + labeled eval queries)
- `make eval-generate` generate eval queries (`EVAL_SUBSET_ID`, `EVAL_PROMPT_VERSION`, `EVAL_TARGET_COUNT`, batching + concurrency knobs)
- `make eval-labels` bootstrap labels from current retrieval results
- `make demo` run init then web server

## Recovery / Error Handling

### 1) Quota / rate-limit errors during `make init` or `make index`
Symptoms: `429 RESOURCE_EXHAUSTED` with `retry in ...s`.

What happens now:
- indexer automatically retries with bounded exponential backoff
- provider retry hints are parsed and honored when present
- request pacing is throttled by `EMBEDDING_REQUESTS_PER_MINUTE`

What to do:
1. Reduce throughput in `.env`:
   - `EMBEDDING_PARALLELISM=1`
   - `EMBEDDING_BATCH_SIZE=8`
   - `EMBEDDING_DIMENSIONS=256`
   - `EMBEDDING_REQUESTS_PER_MINUTE=60`
   - `EMBEDDING_UPSERT_CHUNK_SIZE=10`
2. Re-run:
   - `make index`

Dimension note:
- The SDK call is synchronous `embed_content` with multiple items per request.
  HTTP logs can still show `batchEmbedContents`; that does not mean async batch mode.
- Very large vectors (for example `3072`) can make DuckDB upsert/index steps appear hung.
  If this happens, lower `EMBEDDING_DIMENSIONS` and rebuild (`make db-reset && make index`).

### 2) `make eval` fails with "No eval queries found"
You need to generate queries first:
```bash
make eval-generate
```

Tune generation throughput if needed:
- `EVAL_BATCH_SIZE` (queries per request)
- `EVAL_PARALLELISM` (concurrent generation requests)
- `EVAL_MAX_ROUNDS` (max refill rounds to satisfy unique target)

### 3) `make eval` fails with "No eval labels found"
Bootstrap labels, then rerun:
- `make eval-labels`

Or add expected canonical keys manually to `app.eval_labels` and rerun:
- `make eval`

### 4) HNSW / VSS errors
Rebuild the index explicitly:
- `make vss-index`

### 5) Embedding dimension mismatch
Symptoms: index fails with schema/config mismatch (`FLOAT[3072]` vs `EMBEDDING_DIMENSIONS=256`).

What to do:
1. Reset and rebuild DB + index:
   - `make init`
2. Or align `.env` `EMBEDDING_DIMENSIONS` to existing DB schema if intentionally retained.

## Quality
- `make format-all`
- `make test`
