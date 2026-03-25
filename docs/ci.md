# CI Workflow and PR Status Checks

## Workflow

GitHub Actions workflow: `.github/workflows/pr-ci.yml`

Trigger behavior:
- Runs on `push` to `main` to refresh the default-branch coverage baseline
- Runs on `pull_request` events: `opened`, `reopened`, `synchronize`, `ready_for_review`
- Supports manual runs through `workflow_dispatch`

Active jobs:
- `backend`: Ruff + Pyrefly + Pytest (JUnit + coverage + annotations)
- `migration-stairway`: fixture-seeded pgvector Postgres + Alembic migration validation
- `frontend-unit`: ESLint + TypeScript + Vitest (JUnit + coverage + annotations)
- `coverage`: four-surface coverage gate plus comparison against the latest default-branch baseline
- `e2e-mock`: Playwright against mock route (JUnit + report artifact)
- `ci-summary`: one at-a-glance rollup of all CI lanes plus coverage numbers

Deferred workflow:
- `.github/workflows/e2e-real-ui-smoke.yml` runs after both `PR CI` and `Dependency Review` have succeeded for the same pull-request SHA.
- It brings up the slot-0 snapshot-backed Postgres dependency stack, then runs `make ui-test-e2e-real-ui-smoke` against the checked-out PR head.
- The backend is started with a deterministic local model override, so the smoke path does not depend on a paid or stochastic external model.

## Caching

Configured caches:
- UV cache via `astral-sh/setup-uv` (keyed by `uv.lock`)
- PNPM cache via `actions/setup-node` (keyed by `ui/pnpm-lock.yaml`)
- Playwright browser cache at `~/.cache/ms-playwright`

## Annotation Behavior

Checks emit annotations in GitHub UI for:
- Python lint/type errors (`ruff --output-format=github`, `pyrefly --output-format=github`)
- Frontend lint/type errors (ESLint/TypeScript parsed to GitHub annotation commands)
- Test failures through JUnit + `dorny/test-reporter`

Current gating behavior:
- ESLint is blocking (`--max-warnings=0`).
- TypeScript and all test lanes are blocking.
- `Coverage (backend + frontend)` is blocking when any staged absolute threshold fails.
- `Coverage (backend + frontend)` is also blocking when measured source coverage regresses relative to the latest default-branch baseline.
- `CI Summary` is informational; it summarizes lane status and coverage numbers but does not gate merges on its own.

## Local Equivalent

`make tidy` is the closest local approximation of the blocking unit-level CI lanes. It runs:
- backend Ruff autofix + Pyrefly + coverage-enabled Pytest
- frontend ESLint + TypeScript + coverage-enabled Vitest
- staged local coverage enforcement via `make coverage`

Useful local commands:
- `make backend-coverage`
- `make frontend-coverage`
- `make coverage`
- `bash scripts/ci/run_migration_validation.sh 0`

`make tidy` does not run GitHub annotations or Playwright E2E lanes. The real-UI smoke is deferred to CI after `PR CI` and `Dependency Review` succeed for the PR SHA. Run `make ui-test-e2e-real-ui-smoke` locally only when you need to debug the live CopilotKit or AG-UI path directly.

## Migration Validation

The dedicated `migration-stairway` lane exists to catch downgrade and
re-upgrade problems that a simple `alembic upgrade head` check can miss.

- On pull requests, it runs only when migration-relevant files changed.
- On release validation, the same suite runs before publish/deploy continues.
- It uses `scripts/ci/run_migration_validation.sh`, which starts a clean local
  pgvector Postgres instance, upgrades it, seeds fixture catalog data, and then
  runs:
  - `tests/shared/test_migrations.py`
  - `tests/shared/test_migration_stairway.py`

This keeps migration validation on the same pgvector-capable Postgres image and
fixture catalog inputs used elsewhere in CI, while avoiding brittle dependence
on a published snapshot artifact staying ahead of the migration graph.

## Coverage Reporting

Coverage is measured directly in CI. No hosted coverage service is used.

Current artifacts:
- Backend: `coverage.py` JSON and XML generated during the `backend` job
- Frontend: Vitest LCOV plus `coverage-summary.json` generated during the `frontend-unit` job
- Coverage summary: JSON + Markdown artifact from the `coverage` job

Default-branch baseline flow:
- A successful `push` run on `main` uploads a `coverage-baseline` artifact from the `coverage` job.
- Pull request runs locate the latest successful baseline artifact from `main`.
- The `coverage` job compares current backend/frontend source totals against that baseline inside GitHub Actions.

Pull request coverage signals:
- Backend source coverage
- Backend test execution coverage
- Frontend source coverage
- Frontend test execution coverage
- Patch coverage on changed executable lines in measured files
- Regression status versus the latest default-branch baseline

Authoritative PR surfaces:
- `Coverage (backend + frontend)` check: canonical coverage gate and detailed coverage summary
- `CI Summary` check: compact overview of all CI lanes, including whether optional real-backend e2e was skipped
- Existing suite-level checks (`Backend Pytest`, `Frontend Vitest`, `E2E Playwright Mock`): detailed test failure reporting

Stage A thresholds live in `scripts/coverage_thresholds.py` and are the single source of truth for local and CI enforcement.

Current Stage A thresholds:
- Backend source: `78%`
- Backend tests: `100%`
- Frontend source: `37%`
- Frontend tests: `100%`

Surface definitions:
- Backend source: all files under `src/ikea_agent/**`
- Frontend source: all files under `ui/src/**`
- Backend tests: file-execution coverage for `tests/**/*.py`
- Frontend tests: file-execution coverage for `ui/src/**/*.test.{ts,tsx}` plus helper modules under `ui/src/test/**`

Important implementation detail:
- Backend and frontend source coverage still come from `pytest-cov` and Vitest coverage reports.
- Test surfaces are enforced as execution coverage rather than per-line coverage. This is intentional: the requirement is that every test module and helper is actually exercised, and Vitest hard-excludes `*.test.*` files from its built-in final coverage reports.
- Hypothesis-based pytest tests count normally because they run inside the same measured pytest process.
- `evals/**` and Playwright specs/helpers are excluded from the `100%` test-execution gate.

## No-Secrets / No-Paid-Calls Test Guard

`tests/conftest.py` sets Pydantic AI `override_allow_model_requests(False)` for all backend tests.
This ensures CI fails fast if a test path accidentally attempts a live model call.

## GH CLI Helper

Script: `scripts/gh_ci_status.sh`

What it does:
- Finds the latest `PR CI` run for a PR (or uses explicit run ID)
- Prints pass/fail summary and failed jobs
- Prints PR check status entries
- Fetches and prints check-run annotations (with limit)

Usage:

```bash
scripts/gh_ci_status.sh
scripts/gh_ci_status.sh --pr 123
scripts/gh_ci_status.sh --run 123456789
scripts/gh_ci_status.sh --pr 123 --limit 100
```

Deep triage script: `scripts/gh_ci_pull_run.sh`

What it does:
- Resolves a run by explicit run ID or latest run for a branch.
- Pulls run metadata, jobs, PR checks, annotations, and failed logs into a local folder.
- Generates `summary.md` with top failing files/messages and suggested local commands.

Usage:

```bash
scripts/gh_ci_pull_run.sh --run 123456789
scripts/gh_ci_pull_run.sh --branch epic/my-branch
scripts/gh_ci_pull_run.sh --branch epic/my-branch --required-only
```
