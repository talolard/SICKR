# Phase 3 Implementation Plan (Local M1, Two-DB Architecture)

## Summary

Phase 3 adds three new end-user capabilities and one instrumentation capability:

1. Better ranking quality via local reranking.
2. Gemini-generated recommendation summaries with threaded follow-up.
3. Query expansion that can infer structured filters from natural-language constraints.
4. Full lineage tracking for prompt inputs, model outputs, ranking deltas, and user ratings.

The implementation keeps two DBs by design:

- DuckDB for retrieval/runtime telemetry and analytics.
- Django SQLite for admin-editable prompt/config entities.

## Decisions Locked for This Plan

1. Maintain two DBs in Phase 3.
2. Prompt templates are edited via Django admin-backed models.
3. Runtime provenance and feedback events persist in DuckDB.
4. Reranker target runtime is PyTorch with MPS-first, CPU fallback on M1.
5. Prompt variant comparison supports up to 5 variants and runs variants in parallel.
6. Query expansion default mode is heuristic auto, with explicit user controls.
7. Default filter timing remains embed-first then filter.
8. Feedback shape is thumbs up/down plus reason tags and optional notes.

## User Flows to Implement

## Flow A: Search + expansion + rerank

1. User submits query on `/`.
2. Expansion mode (`auto|on|off`) is resolved.
3. If expansion applies, inferred filters are materialized and shown in UI chips.
4. Retrieval runs with current semantic search path.
5. Reranker reorders top-N candidates.
6. Results render with "Show without filters" action for expansion-applied filters.
7. Rerank-diff link navigates to before/after comparison page.

## Flow B: Prompt variant comparison

1. User chooses prompt variants and executes compare run.
2. System renders each system prompt template with shared query/result context.
3. Gemini calls execute in parallel.
4. Side-by-side UI shows per-variant summary + item reasoning + metadata.
5. Variant outputs are persisted for replay and analysis.

## Flow C: Follow-up conversation

1. User opens one variant output and asks follow-up questions.
2. System sends prior context plus follow-up.
3. Turn is persisted in conversation history.
4. Sidebar exposes conversation history for quick navigation.

## Flow D: Feedback capture

1. User rates full turn (thumb + reasons + note).
2. User rates specific recommended items.
3. Ratings persist with linkage to request, variant, turn, and product key.

## Data Model and API Changes

### Django SQLite models (admin/config plane)

1. `SystemPromptTemplate`
   - key/version/template text, active flag, metadata JSON.
2. `PromptVariantSet`
   - named group of templates for compare runs.
3. `FeedbackReasonTag`
   - scope (`turn`/`item`) and polarity (`up`/`down`) tags.
4. `ExpansionPolicyConfig`
   - heuristic rules and confidence threshold knobs.

### DuckDB tables (runtime/analytics plane)

1. `app.search_request_v2`
2. `app.search_expansion_event`
3. `app.search_result_snapshot`
4. `app.prompt_run`
5. `app.prompt_response_turn`
6. `app.conversation_thread`
7. `app.conversation_message`
8. `app.feedback_turn_rating`
9. `app.feedback_item_rating`

Each table must include stable IDs and timestamps, and key foreign-link fields (request ID, thread ID, run ID, turn ID).

### Python typed contracts

Add explicit typed contracts in `shared/types.py` (or new module if file grows too large):

1. mode literals (`QueryExpansionMode`, `FilterTimingMode`, `RankingStage`)
2. prompt/response contracts for summary outputs
3. expansion output contract
4. feedback payload contracts

## Implementation Workstreams

## W1: Schema and persistence foundation

1. Add SQL migration scripts for new DuckDB Phase 3 tables/views.
2. Add repository APIs for new writes/reads.
3. Keep SQL in `sql/` and repository methods thin.

## W2: Admin/config foundation

1. Add Django model definitions and admin registration.
2. Add validation constraints (unique keys, version rules, active state rules).
3. Add fixtures/seed helper for initial prompt templates and reason tags.

## W3: Query expansion service

1. Build Gemini structured expansion call.
2. Add heuristic gate for `auto` mode.
3. Map expansion output into retrieval filters.
4. Persist expansion events and applied/non-applied decisions.

## W4: Reranking service

1. Add HF cross-encoder scoring pipeline.
2. Device selection: MPS then CPU fallback.
3. Rerank top candidate set and keep semantic baseline ranks.
4. Persist before/after snapshots for diff analysis.

## W5: Prompt compare + summary service

1. Render system prompts via Django template engine.
2. Execute up to 5 variants in bounded parallelism.
3. Parse structured outputs and persist prompt run lineage.
4. Return side-by-side display model.

## W6: Conversation and feedback UI

1. Add routes/templates for prompt lab and conversation threads.
2. Add ratings controls on turns and items.
3. Add rerank-diff visualization page.

## W7: Testing and documentation

1. Add unit tests for expansion/rerank/prompt parsing/repositories.
2. Add integration tests for new end-to-end flows.
3. Update docs in `docs/` and data schema index.

## Route and UI Additions

1. `/prompt-lab` compare selected system prompt variants.
2. `/conversations/<thread_id>` follow-up chat + rating controls.
3. `/analysis/rerank-diff/<request_id>` before/after ranking diff.

The existing `/` search page remains entrypoint and gains new controls:

- expansion mode selector
- applied-filter source chips
- actions to suppress expansion filters
- links to prompt lab and rerank diff

## Operational and Performance Expectations

1. Phase 3 must remain runnable on local M1.
2. Default model footprints should be conservative.
3. Prompt variant execution must be parallel but bounded.
4. Failures should be isolated per variant (partial success UI).

## Test Cases and Scenarios

## Unit tests

1. Expansion parser validation and heuristic gating.
2. Prompt template rendering determinism and hash generation.
3. Reranker order stability and fallback behavior.
4. Feedback validation for scope/polarity/tag constraints.

## Integration tests

1. Search with `auto|on|off` expansion modes.
2. Rerank snapshot persistence before/after.
3. Parallel variant execution with mixed success/failure.
4. Follow-up conversation turn persistence.
5. Turn + item ratings persistence and queryability.

## Acceptance scenarios

1. A local user can run full flow from search to rating without manual DB surgery.
2. Every summary turn can be traced back to specific system prompt template/version.
3. Ranking deltas are explorable by request.
4. Expansion behavior is auditable (triggered, confidence, applied filters).

## Rollout Sequence

1. Deliver W1 + W2 first (schema + admin config).
2. Deliver W3 + W4 (expansion + rerank core).
3. Deliver W5 + W6 (prompt compare, conversations, ratings).
4. Deliver W7 (tests/docs hardening) and finalize.

Each workstream is tracked as a bead task under one Phase 3 epic.

## Risks and Mitigations

1. Model runtime on M1 can be variable.
   - Mitigation: explicit fallback, batch-size controls, bounded candidate count.
2. Two-DB coordination drift (template/config vs runtime events).
   - Mitigation: store template key/version/hash in every runtime event row.
3. UI complexity growth.
   - Mitigation: isolate pages by workflow and keep `/` focused on core search.

## Assumptions and Defaults

1. No authentication rollout in Phase 3; keep anonymous session refs plus optional `user_ref` fields.
2. Existing retrieval SQL remains canonical semantic baseline.
3. Gemini remains generation provider for summary and expansion tasks.
4. New Phase 3 schema changes are additive and backward-compatible with current local setup.
