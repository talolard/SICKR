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

The dialog also loads `GET /api/traces/recent?limit=5` so developers can quickly find the latest
saved bundles and their on-disk directories without leaving the chat page.

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
The UI keeps this as a partial-success state and surfaces the saved directory even when issue
creation does not complete.

### Additional trace follow-ups

- The save-trace dialog now shows recent saved traces and includes the saved directory in success messaging.
- The Next trace proxy translates missing backend trace routes into a clearer configuration-mismatch error.
- Trace bundles redact sensitive values in archived event payloads and console logs before writing them to disk.
- The UI proxies both `POST /api/traces` and `GET /api/traces/recent`, so frontend/backend flag drift fails clearly instead of as a generic 404.

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

- bundle items must already be grounded by a prior `run_search_graph` result in the current run;
  ungrounded product IDs are rejected instead of being silently hydrated
- `pricing_complete` reports when totals are incomplete because one or more items have no price
- `duplicate_items` reports when repeated product entries were merged into one combined quantity
- `budget_max_eur` still reports pass/fail/unknown based on the user budget ceiling

### UI rendering

On wide screens, the search agent page now uses three distinct surfaces:

- agent inspector
- main search workbench
- chat sidebar

Bundle proposals render in the main workbench, outside the chat transcript.
Each bundle is collapsed by default and shows its title, total, item count, and summary metadata.
Expanding a bundle reveals:

- validator badges
- budget cap context
- a bounded scroll area for line items
- the per-item rationale (`reason`) and description
- explicit pending-price markers when totals are incomplete

The in-chat renderer remains minimal and simply confirms that the bundle was added to the side panel.
