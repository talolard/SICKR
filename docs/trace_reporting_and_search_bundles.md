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

## Batched search queries

`run_search_graph` now accepts `queries: SearchQueryInput[]` instead of a single scalar query.
Even single searches should be represented as a one-element array.

### Search behavior

- query texts are embedded in batches through the runtime embedder
- retrieval, rerank, and diversification still run per query
- explicit `candidate_pool_limit` values override the default pool size

## Bundle proposals

The search agent also has a separate `propose_bundle` tool for structured recommendations.

### Payload shape

A bundle proposal contains:

- `title`
- optional `notes`
- optional `budget_cap_eur`
- `items[]` with `item_id`, `quantity`, and `reason`

The backend hydrates product metadata, computes totals, runs validations, and appends the proposal to
search-agent state.

### UI rendering

Bundle proposals are rendered in a side panel on the search agent page, outside the chat transcript.
The tool renderer in chat remains minimal and simply acknowledges that the bundle was added.


## Additional trace follow-ups

- The save-trace dialog now shows recent saved traces and includes the saved directory in success messaging.
- The Next trace proxy translates missing backend trace routes into a clearer configuration-mismatch error.
- Trace bundles redact sensitive values in archived event payloads and console logs before writing them to disk.
- The UI proxies both `POST /api/traces` and `GET /api/traces/recent`, so frontend/backend flag drift fails clearly instead of as a generic 404.
