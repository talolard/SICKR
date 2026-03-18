# Towels March UI Follow-Ups

## Scope

Implement four related follow-ups on a single branch for epic `tal_maria_ikea-1xm`:

1. add clickable product links to search bundle items
2. keep the chat panel open as part of the main viewport
3. clarify durable-facts guidance in the shared preference instruction text
4. replace the agent-composition panel with collected known facts

## Design Notes

- Bundle links should use the existing product URL already present in retrieval results. The typed bundle proposal payload currently drops that field, so the change needs backend and frontend schema updates.
- Known facts are thread-scoped revealed preferences. The UI should show the individual stored statements, ordered consistently, rather than agent composition details.
- The agent page is the integration point for both the known-facts panel and the persistent-open chat layout, so subtask implementations should keep their write scopes disjoint and leave page-level wiring for final integration.
- Prompt guidance should explicitly separate durable facts and household context from turn-specific shopping intent.

## Validation

- targeted Python tests for revealed-preference and bundle state contracts
- targeted UI vitest coverage for bundle links, known-facts panel, and persistent chat behavior
- `make tidy` before finalizing the branch
