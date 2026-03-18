## Summary

Complete the post-floor-plan cleanup epic in one scoped pass by splitting the
shared agent page into typed orchestration seams, adding direct tests on the
shared page and CopilotKit session surface, and moving product-title enrichment
into durable catalog metadata instead of UI formatting.

## Refactor boundary

- Keep `ui/src/app/agents/[agent]/page.tsx` as the route entrypoint only.
- Extract stateful concerns into typed hooks for:
  - agent catalog and metadata loading
  - known-facts loading
  - search bundle hydration/persistence
  - transcript bootstrap/persistence and agent state sync
  - floor-plan preview persistence
- Extract layout/header rendering into a small shared shell component so search
  and non-search branches are readable without changing behavior.

## Coverage targets

- Add direct Vitest coverage on the shared agent page for:
  - thread snapshot rehydration
  - attachment capability wiring
  - search versus floor-plan layout branching
- Add direct Vitest coverage on `CopilotKitProviders` for:
  - URL or storage bootstrap
  - thread creation
  - fallback behavior when selecting a non-resumable thread

## Product display-title path

- Add a durable `display_title` column to `app.products_canonical`.
- Derive missing display titles from the best available metadata in this order:
  - IKEA product URL slug
  - description text
  - fallback to the original family name
- Run the derivation in backend startup against missing rows and keep runtime UI
  contracts simple by sourcing `product_name` from `display_title` once present.

## Validation

- Targeted Vitest on the new page/provider tests plus touched CopilotKit/renderer
  surfaces as needed
- Targeted pytest on retrieval/search metadata-title flow
- `make tidy`
- `make ui-test-e2e-real-ui-smoke`
