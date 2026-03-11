# Trace reporting and search bundles

## Developer trace capture

The app now supports a developer-only trace reporting flow for CopilotKit AG-UI threads.

### Enablement

Backend:

- `TRACE_CAPTURE_ENABLED=true`
- `TRACE_ROOT_DIR=traces`

Frontend:

- `NEXT_PUBLIC_TRACE_CAPTURE_ENABLED=1`

Leave these disabled in production-like deployments.

### UI flow

On an agent page with an active thread, the header shows a save-trace icon when the flag is enabled.
The dialog requires a title and accepts an optional description. Submitting sends the current thread
and agent identifiers to `POST /api/traces`.

### Saved bundle layout

Each saved report is written under `traces/<trace-id>/` with:

- `metadata.json`
- `trace.json`
- `report.md`
- `console_log.json` when browser console capture is included

The backend reconstructs the trace from AG-UI events archived in the run history repository, so the
feature does not depend on the CopilotKit inspector export button.

### Beads integration

On success, the server creates:

- one Beads epic for the trace report
- one child triage task

If Beads creation fails, the trace bundle is still saved and the API returns `saved_without_beads`.

## Batched search queries

`run_search_graph` accepts `queries: SearchQueryInput[]` instead of a single scalar query.
Even single searches must be represented as a one-element array.

### Search behavior

- query texts are embedded in batches through the runtime embedder
- retrieval, rerank, and diversification still run per query
- explicit `candidate_pool_limit` values override the default pool size
- query-level logs now include `embedding_duration_ms`, `retrieval_duration_ms`,
  `rerank_duration_ms`, and `diversify_duration_ms`
- the pipeline skips similarity lookup/diversification when a query has fewer than two reranked
  candidates or only one result can be returned, because diversification cannot improve that case

## Bundle proposals

The search agent has a separate `propose_bundle` tool for structured recommendations.

### Payload shape

A bundle proposal contains:

- `title`
- optional `notes`
- optional `budget_cap_eur`
- `items[]` with hydrated product metadata, quantities, and reasons
- `validations[]` with stable kinds: `budget_max_eur`, `pricing_complete`, and `duplicate_items`

Search-agent shared state now stores typed bundle proposal models instead of raw dictionaries.

### Persistence

Bundle proposals are persisted server-side per thread and run in `bundle_proposals`.
The search page reads saved proposals from `/api/threads/{thread_id}/bundle-proposals` and merges
that history with the local append-only browser cache so proposals survive reloads and device swaps.

### Validation behavior

The backend hydrates product metadata, computes totals, and runs richer bundle validation:

- `pricing_complete` reports when totals are incomplete because one or more items have no price
- `duplicate_items` reports when repeated product entries were merged into one combined quantity
- `budget_max_eur` still reports pass/fail/unknown based on the user budget ceiling

### UI rendering

Bundle proposals are rendered in a side panel on the search agent page, outside the chat transcript.
The panel shows validator badges, budget cap context, and explicit pending-price markers for line
items whose totals are not fully known. The in-chat renderer remains minimal and simply confirms
that the bundle was added to the side panel.
