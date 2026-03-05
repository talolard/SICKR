# 2. Embedding Text Strategy and Batch Indexing Job

## Objective
Create an independent indexing job that builds enriched embedding text and writes vectors for catalog rows.

## Where Work Happens
- `src/ikea_agent/ingest/` for indexing pipeline modules and CLI entrypoints.
- `src/ikea_agent/shared/` for common typed models/config/logging helpers.
- `sql/` for embedding input materialization and write/update SQL.
- `docs/` for operation and runbook notes.

## Key Requirements from Notes
- Job must be separate from the web app.
- Must support subset runs (small slices for iteration).
- Must use Gemini embeddings (query/document task type chosen deliberately).
- Batch mode preferred when ETA/completion visibility is available.

## Tasks
- Define embedding input schema:
  - Metadata header block (category, dimensions, price, material, etc.).
  - Main descriptive text body.
  - Versioned text-construction strategy for experiments.
- Implement an experiment surface:
  - Strategy class/function variants for enriched text construction.
  - Config switch to choose strategy per run.
- Build indexing workflow:
  - Full and subset execution modes.
  - Resume/retry behavior for failed batches.
  - Progress and ETA logging.
- Persist outputs:
  - Vector table rows with model, strategy version, timestamp.
  - Index run metadata table (run_id, scope, status, timing).

## Deliverables
- SQL + code path to materialize embedding input text.
- Independent embedding/indexing job command.
- Operational docs for full vs subset runs.

## Exit Criteria
- A subset run and full run both complete successfully.
- Vectors are written and traceable to run metadata and strategy version.
- Re-running is idempotent or explicitly upsert-based.
