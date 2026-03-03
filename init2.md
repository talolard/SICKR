# init2: Scaffolding Task List (Pre-Development)

This plan is the ordered task list to set up the project foundation only. It intentionally stops before building app features.

## 1. Align scope and freeze initial decisions

- Confirm final stack decisions in writing:
  - Python + UV
  - Ruff (lint + format)
  - Pyrefly for type checking
  - Pytest
  - GCP + Gemini embeddings
  - DuckDB primary local store (SQLite optional only if needed)
  - Hugging Face reranker workflow (later integration, scaffold now)
- Freeze dependency plan (no coding yet), split into:
  - Runtime deps (expected): Google/GCP SDKs, Gemini client, DuckDB, dotenv/settings helper, structured logging helper
  - ML/search deps (expected): sentence-transformers/transformers for reranking, optional torch (MPS-aware)
  - Dev deps: ruff, pytest, pyrefly, pytest-cov, pre-commit (optional)
  - Decision log: keep `candidate` vs `committed` status per dependency
- Define configuration management approach before implementation:
  - Canonical source for config keys (`docs/configuration.md`)
  - Local secret handling (`.env` + `.env.example`, never commit secrets)
  - Config layering order (defaults -> env file -> shell env -> CI overrides)
  - Validation policy (preflight/startup fails on missing required keys)
- Define the first non-goals list (what we are explicitly not building in setup).

## 2. Create repository structure

- Create source/test layout:
  - `src/`
  - `tests/`
- Create project operations/docs layout:
  - `plans/` (agent task plans)
  - `docs/`
  - `docs/data/`
  - `sql/` (all SQL files, schema/migrations/queries/pragmas)
  - `scripts/` (small reproducible CLI helpers)
- Create only top-level `data/` now.
- Defer `data/` subdirectory design (`raw/processed/vector/queries` etc.) until the data architecture step.
- Keep your existing `external_docs/` folder untouched.

## 3. Initialize Python project with UV

- Create `pyproject.toml` with:
  - Project metadata
  - `src` package configuration
  - Dev dependencies (ruff, pytest, pyrefly, optional mypy off by default)
- Configure UV-managed environment and lockfile.
- Ensure commands run without manual `PYTHONPATH` hacks.

## 4. Configure linting, formatting, and typing

- Add thorough Ruff config in `pyproject.toml` (or `ruff.toml`) with strict rules enabled.
- Configure Ruff format profile and import sorting.
- Add Pyrefly configuration for strict static analysis.
- Define quality gates:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pyrefly ...`
  - `uv run pytest`

## 5. Configure VS Code workspace tooling

- Add `.vscode/settings.json` with:
  - Format-on-save enabled
  - Ruff lint + format on save
  - Python test discovery for pytest
  - Pyrefly integration in editor tasks/settings
- Add `.vscode/extensions.json` recommendations.
- Add `.vscode/tasks.json` for one-command local quality checks.

## 6. Configure testing baseline

- Add `tests/` bootstrap with one smoke test and typed test style.
- Add pytest config (in `pyproject.toml` or `pytest.ini`) for:
  - Test paths
  - Verbosity/default options
  - Markers for unit/integration if desired
- Ensure `uv run pytest` passes in a clean environment.

## 7. Establish logging and debugging standards

- Define logging conventions in `docs/logging.md`:
  - Log format
  - Levels
  - Required context fields (request/query IDs, pipeline step)
- Add a minimal logging config module scaffold (no app logic).
- Document how to run locally with debug logging enabled.

## 8. Set up local data architecture (DuckDB-first)

- Create DuckDB database path convention (e.g. under `data/processed/`).
- Create SQL-first structure in `sql/`:
  - Schema creation
  - Pragmas/settings
  - Ingestion statements
  - Query templates for analysis/search preparation
- Document policy: SQL lives in `.sql` files, avoid embedding SQL in Python unless justified.
- Define retention rule for raw IKEA CSV (delete after load is allowed).

## 9. Define data model and documentation process

- Create `docs/data/index.md` with:
  - Source dataset description
  - Table definitions
  - Column dictionary
  - Vector storage strategy
  - Query log schema
- Add update procedure: every schema change must update docs in `docs/data/`.

## 10. Scaffold embedding and reranking pipeline interfaces

- Create placeholder module boundaries only (no production implementation):
  - Data loader interface
  - Embedding generator interface (Gemini)
  - Vector persistence interface
  - Reranker interface (Hugging Face)
- Define input/output typed objects for each stage.
- Add docs page describing end-to-end planned pipeline and failure points.

## 11. Configure GCP integration prerequisites (without running production jobs)

- Document required env vars, auth method, and project/region assumptions in `docs/gcp_setup.md`.
- Add `.env.example` (non-secret placeholders only).
- Add a preflight command checklist for validating credentials and API enablement.

## 12. Enforce local workflow and automation entrypoints

- Add a `Makefile` (or task runner) with at least:
  - `make lint`
  - `make format`
  - `make typecheck`
  - `make test`
  - `make tidy` (aggregate autofix target)
- Ensure each target delegates to UV commands.
- Document “one command before commit” workflow.

## 13. Set project-local Git identity safeguards

- Configure repo-local git identity to your public account (`Talolard`) and verify:
  - `user.name`
  - `user.email`
  - SSH host alias behavior for correct key/account
- Add `docs/git_identity.md` with verification commands and expected output patterns.
- Add a quick pre-push check to avoid accidental work-account pushes.
- Bonus - signed commits with the correct key if feasible.

## 14. Create AGENTS.md for this repo

- Capture collaboration practices, coding standards, toolchain rules, and docs update expectations.
- Include:
  - Planning files go to `plans/`
  - Task completion requires docs update under `docs/`
  - SQL-first database workflow
  - Typing/testing/linting expectations
  - Git identity requirement (public account)
  - Code practices, rigorous types, no Any, no raw generics, find stubs for libs or make the minimal that we need . Use dataclasses, use discriminated unions with kind keyword.
  -

## 15. Initialize core documentation set

- Create `docs/index.md` with:
  - Project overview
  - Local setup steps
  - Development workflow
  - Data docs section pointing to `docs/data/`
  - External docs section (link only; do not modify your existing `external_docs/` now)
- Add initial docs pages referenced above so links are valid.

## 16. Final scaffolding validation pass

- Run full local quality suite:
  - lint, format check, typecheck, tests
- Run a dry-run of data initialization path (schema creation only).
- Verify a new contributor can bootstrap from docs alone.
- Produce a short “scaffold complete” checklist with any follow-up gaps.

---

## Exit Criteria (Before Feature Development)

- Tooling is reproducible via UV.
- Editor auto-format/lint/typecheck behavior is configured.
- Tests run and pass.
- DuckDB + SQL-first layout is in place.
- Core docs + AGENTS.md + planning conventions are established.
- Git identity is pinned to the public account for this repo.
- No application feature code has been started yet.
