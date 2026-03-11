# Plan: Trace Reporting Intake and Batched Search Bundles

## Goal

Implement two related runtime improvements:

1. A developer-only trace reporting flow that saves the current agent-thread trace to local disk and creates Beads work for follow-up.
2. A search-agent tooling redesign that always accepts batched query objects, batches embeddings, and renders optional bundle proposals outside the chat transcript.

## Scope

- Backend trace capture, persistence, and typed `/api/traces` endpoint.
- UI save-trace affordance, modal, and Next proxy route.
- Search contract migration from scalar query inputs to batched query objects.
- Bundle proposal tool plus side-panel rendering for search-only pages.
- Docs, tests, and behavioral verification updates.

## Key Decisions

- The trace source of truth is backend-canonical AG-UI run history plus archived outbound AG-UI events.
- Saved traces target the current thread for the current agent.
- Beads creation is best-effort and must not block saving the trace bundle.
- `run_search_graph` is migrated in place to accept `queries=[...]`, even for one search.
- Only the embedding step is batched in the first cut; retrieval/rerank/diversification remain per query.
- Bundles are optional and append-only; the rich bundle view lives outside the chat transcript.
