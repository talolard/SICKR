# CI Workflow and PR Status Checks

## Workflow

GitHub Actions workflow: `.github/workflows/pr-ci.yml`

Trigger behavior:
- Runs on `push` to `main` to refresh the default-branch coverage baseline
- Runs on `pull_request` events: `opened`, `reopened`, `synchronize`, `ready_for_review`
- Supports manual runs through `workflow_dispatch`

Active jobs:
- `backend`: Ruff + Pyrefly + Pytest (JUnit + coverage + annotations)
- `frontend-unit`: ESLint + TypeScript + Vitest (JUnit + coverage + annotations)
- `coverage`: GitHub-native backend/frontend coverage comparison against the latest default-branch baseline
- `e2e-mock`: Playwright against mock route (JUnit + report artifact)
- `ci-summary`: one at-a-glance rollup of all CI lanes plus coverage numbers

Disabled scaffold job:
- `e2e-all-models` is present but gated with `if: ${{ false }}`.
- It is intentionally disabled to avoid secret/model spend on every PR.
- Enable it later by changing the condition and wiring required secrets.

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
- `Coverage (backend + frontend)` is blocking when backend or frontend total coverage regresses relative to the latest default-branch baseline.
- `CI Summary` is informational; it summarizes lane status and coverage numbers but does not gate merges on its own.

## Coverage Reporting

Coverage is measured directly in CI. No hosted coverage service is used.

Current artifacts:
- Backend: `coverage.py` JSON and XML generated during the `backend` job
- Frontend: Vitest LCOV plus `coverage-summary.json` generated during the `frontend-unit` job
- Coverage summary: JSON + Markdown artifact from the `coverage` job

Default-branch baseline flow:
- A successful `push` run on `main` uploads a `coverage-baseline` artifact from the `coverage` job.
- Pull request runs locate the latest successful baseline artifact from `main`.
- The `coverage` job compares current backend/frontend totals against that baseline inside GitHub Actions.

Pull request coverage signals:
- Backend total coverage
- Frontend total coverage
- Patch coverage on changed executable lines in measured files
- Regression status versus the latest default-branch baseline

Authoritative PR surfaces:
- `Coverage (backend + frontend)` check: canonical coverage gate and detailed coverage summary
- `CI Summary` check: compact overview of all CI lanes, including whether optional real-backend e2e was skipped
- Existing suite-level checks (`Backend Pytest`, `Frontend Vitest`, `E2E Playwright Mock`): detailed test failure reporting

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
