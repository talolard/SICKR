# Floor Planner Tooling Implementation Plan

## Intent
Implement `spec/agent_tools.md` by introducing a typed tools package with a floor-planner tool, a bridge pattern for agent decorators, extensive tests, docs, and sample data fixtures.

## Scope
- Add `tal_maria_ikea.tools` package and floor-planner components.
- Add typed Pydantic models for room geometry and wall-linked openings.
- Add renderer integration using the `renovation` package to output local PNG files.
- Add an agent bridge that can register a decorated tool on pydantic-ai style agents.
- Add docs and external docs notes for the dependency.
- Add fixture-driven tests for valid and invalid room definitions.

## Out of Scope
- End-to-end integration with a production pydantic-ai graph runtime (none currently in this branch).
- Persisting generated image artifacts in git.

## Validation
- `make format-all`
- `make test`
- `make tidy`

## Deliverables
- New source modules under `src/tal_maria_ikea/tools/`.
- New tests under `tests/tools/`.
- New sample fixtures under `tests/fixtures/floor_planner/`.
- New docs under `docs/tools/` plus docs index updates.
