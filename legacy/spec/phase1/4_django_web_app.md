# 4. Django Web App (Local Only)

## Objective

Ship a local Django UI where users submit natural-language product queries and review ranked results.

## Where Work Happens

- `src/ikea_agent/web/` for Django settings, urls, apps, forms, and views.
- `src/ikea_agent/web/templates/` for page templates and reusable snippets.
- `tests/web/` for view/form/response tests.
- `docs/` for local run and debugging instructions.

## Tasks

- Initialize Django project using latest release.
- Build one search page with:
  - Query input.
  - Request-state spinner while retrieval is running.
  - Result list (name, category, dimensions, price, brief rationale).
  - Empty/error states.
- Define and implement a visual style guide for Phase 1:
  - Typography scale and font choices.
  - Color tokens and contrast/accessibility rules.
  - Spacing system, container widths, and responsive breakpoints.
  - Reusable component snippets (search form, result card, pagination bar, status banner).
- Define user flows for local-only usage (no signup):
  - Search submit and loading state.
  - Result exploration flow (first page, subsequent pages).
  - Optional item-selection/saved-list behavior for shortlisting during a session.
- Wire request flow:
  - Form submit -> retrieval call -> template render.
  - Persist query log row for each request.
  - Implement pagination strategy and page-size defaults.
- Add local-only DX features:
  - Clear run instructions.
  - Debug logging toggle.

## Deliverables

- Django app with a functional semantic search page.
- Reusable template partials/snippets with a consistent visual system.
- Docs describing local run and common troubleshooting paths.
- Documented user-flow spec for search, loading, results, pagination, and optional shortlist behavior.

## Exit Criteria

- User can run locally and submit natural-language queries.
- Relevant ranked results render from DuckDB-backed retrieval.
- No embedding-generation responsibilities inside Django runtime.
