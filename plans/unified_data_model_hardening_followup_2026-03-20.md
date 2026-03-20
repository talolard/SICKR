## Summary

Land the post-review hardening work for the unified room-project-thread rollout
as one stacked follow-on branch over PR 85. The branch should fix the database
correctness gaps found in review, repair the active-thread browser fixture that
no longer matches backend-owned thread bootstrap, and extract the repeated
toolset and repository patterns that the rollout made more obvious.

Root bead: `tal_maria_ikea-cl4.18`

Base branch:
- `origin/epic/tal_maria_ikea-cl4-delete-app-level-archive-persistence-and`

Companion docs:
- `spec/unified_data_model_analysis.md`
- PR 85 review comment

## Fix scope

### 1. Canonical transcript append safety

- Replace application-side `max(sequence_no) + 1` allocation for
  `thread_message_segments` with a database-safe append strategy.
- Keep canonical ordering per thread without allowing duplicate sequence values
  under overlapping writes.
- Add focused persistence coverage that proves the append path is collision-safe.

### 2. Floor-plan revision integrity and performance

- Add the room-scoped uniqueness contract the repository already assumes for
  `floor_plan_revisions`.
- Add the composite index support needed for room-plus-revision lookups and
  latest-revision queries.
- Keep the repository query shape aligned with the new index definitions.

### 3. Thread activity metadata

- Update thread-scoped durable writes so `threads.last_activity_at` reflects
  actual latest activity rather than only thread creation.
- Cover the transcript/history path explicitly and include any other rollout
  write path that should affect room-thread ordering.
- Extend room-thread query tests so ordering matches persisted activity.

## Extraction scope

### 4. Shared persisted-tool-result helper

- Remove the repeated image-analysis pattern that:
  - runs a tool
  - resolves or reuses run identity
  - persists the typed result
  - returns the typed value unchanged
- Keep agent prompts and tool return contracts explicit at call sites.

### 5. Shared existing-run resolution

- Replace duplicated `_resolve_existing_run_id` helpers across persistence
  repositories with one shared typed helper.
- Keep repository ownership boundaries clear; do not introduce a generic
  inheritance-heavy repository layer.

### 6. Shared toolset composition helper

- Extract the repeated shared-plus-local toolset assembly used by the agent
  toolset builders.
- Preserve explicit capability differences per agent and avoid hiding tool names
  or availability behind dynamic registration magic.

## Browser coverage repair

### 7. Active-thread search fixture

- Update the Playwright fixture in `ui/e2e/mock-chat.spec.ts` so the seeded
  active-thread search page matches the backend-owned thread bootstrap model.
- Keep the compact search page assertions, but stop relying on pre-rollout
  local-storage-only thread assumptions.

## Validation

- Targeted pytest for touched persistence repositories and thread query paths.
- Targeted Vitest or Playwright coverage for touched UI and toolset seams.
- `make tidy`
- Focused rerun of `ui/e2e/mock-chat.spec.ts`
