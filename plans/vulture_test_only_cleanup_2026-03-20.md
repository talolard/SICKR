## Context

Run a narrow dead-code cleanup driven by `uvx vulture src --sort-by-size`.
This pass only removes runtime code that is either:

- exercised exclusively by tests, or
- left fully unused inside the same small surface that becomes effectively empty.

## Scope

- Delete src helpers that only exist to support tests:
  - `build_postgres_sqlalchemy_url`
  - `product_id_from_canonical_key`
  - `SearchRepository.list_search_runs`
  - retrieval schema bootstrap helper under `src/ikea_agent/shared/bootstrap.py`
- Delete the display-title backfill helper while preserving the still-used title-derivation helper.
- Trim room-3d repository write/read helpers that are only exercised by repository tests.
- Remove or rewrite tests so surviving coverage still targets active runtime behavior.
- Keep script-backed helpers that `vulture` reports only because this pass scans `src/` but not `scripts/`.

## Validation

- Run targeted pytest coverage for touched surfaces.
- Run `make tidy`.
- Rerun `uvx vulture src --sort-by-size` and summarize remaining candidates.
