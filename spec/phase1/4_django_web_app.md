# 4. Django Web App (Local Only)

## Objective
Ship a local Django UI where users submit natural-language product queries and review ranked results.

## Where Work Happens
- `src/tal_maria_ikea/web/` for Django settings, urls, apps, forms, and views.
- `src/tal_maria_ikea/web/templates/` for page templates and reusable snippets.
- `tests/web/` for view/form/response tests.
- `docs/` for local run and debugging instructions.

## Tasks
- Initialize Django project using latest release.
- Build one search page with:
  - Query input.
  - Result list (name, category, dimensions, price, brief rationale).
  - Empty/error states.
- Wire request flow:
  - Form submit -> retrieval call -> template render.
  - Persist query log row for each request.
- Add local-only DX features:
  - Clear run instructions.
  - Debug logging toggle.

## Deliverables
- Django app with a functional semantic search page.
- Minimal template set using default Django rendering.
- Docs describing local run and common troubleshooting paths.

## Exit Criteria
- User can run locally and submit natural-language queries.
- Relevant ranked results render from DuckDB-backed retrieval.
- No embedding-generation responsibilities inside Django runtime.
