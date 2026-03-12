# CopilotKit Layout And Bundle Panel Plan

## Problem

The search agent screen currently lets the Copilot chat sidebar dominate the working area, which leaves the middle panel cramped. The bundle panel also expands into a large table immediately, so item rationale is easy to miss and one bundle can consume most of the available height.

## Approach

1. Reshape the search page into three explicit wide-screen surfaces:
   - inspector
   - main workbench
   - chat sidebar
2. Keep the chat sidebar in its own outer column so the middle workbench keeps stable width.
3. Replace the always-open bundle table with collapsed bundle cards that show:
   - bundle name
   - total
   - item count
4. When expanded, render bundle items in a bounded scroll region and surface the item rationale prominently.
5. Add focused UI tests for the collapsed and expanded bundle states.

## Validation

- `cd ui && pnpm test -- SearchBundlePanel`
- `make tidy`
- `make ui-test-e2e-real-ui-smoke`
