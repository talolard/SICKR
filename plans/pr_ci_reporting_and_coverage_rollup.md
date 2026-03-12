# PR CI Reporting And Coverage Rollup

## Summary

Make pull requests answer these questions at a glance:

- Which test lanes ran?
- Which lanes passed or failed?
- Did end-to-end coverage run?
- What is backend and frontend coverage now?
- Did this pull request reduce coverage within the changed scope or overall project coverage?

The current workflow already publishes per-suite JUnit test reports via `dorny/test-reporter`.
The missing pieces are:

- one concise PR-visible rollup that summarizes the lanes,
- measured backend and frontend coverage totals in CI plus comparison,
- PR-facing coverage status in GitHub itself,
- documentation that explains which signals are authoritative.

## Why We Need This

Today a green PR mostly means "the workflow jobs passed". That is useful, but it does not give a reviewer a compact answer to what was actually exercised.

The specific gap is not basic test execution. We already run backend, frontend unit, and Playwright mock lanes, and we already publish JUnit-derived test reports in GitHub.
The missing reviewer ergonomics are:

- no single rollup view that says "backend tests passed, frontend unit passed, mock e2e passed, real-backend e2e skipped",
- no coverage number surfaced on the PR,
- no clear "coverage did not regress" signal,
- no explicit statement of which tool owns which surface.

## Current State

From `.github/workflows/pr-ci.yml` and `docs/ci.md`:

- Backend tests publish JUnit and a `Backend Pytest` check.
- Frontend unit tests publish JUnit and a `Frontend Vitest` check.
- Mock Playwright tests publish JUnit and an `E2E Playwright Mock` check.
- Lint and typecheck diagnostics already emit GitHub annotations directly.
- The full real-backend e2e lane exists but is intentionally disabled.
- Coverage configuration exists in both Python and Vitest config, but CI does not yet generate and publish PR-facing coverage results.

## Goals

- Keep the existing job-level checks because they are already useful and stable.
- Add one machine-generated summary that is easy to scan without opening raw logs.
- Measure backend and frontend coverage totals in CI.
- Publish PR-facing coverage results that distinguish overall project coverage from changed-scope regression.
- Keep the implementation small and incremental.

## Non-Goals

- Do not replace the whole workflow system.
- Do not move all diagnostics into reviewdog just because it exists.
- Do not enable the expensive real-model e2e lane on every PR as part of this work.
- Do not introduce an external coverage SaaS such as Codecov.
- Do not redesign unrelated branch-protection or merge-queue policy.

## Core Design Decisions

### 1. Keep `dorny/test-reporter` for test suites

The repo already emits JUnit and publishes suite-level reports successfully.
We should keep that path rather than swapping reporters unless we find a concrete limitation.

### 2. Add a GitHub-native summary layer

Add one summary-producing step or job that writes to `GITHUB_STEP_SUMMARY` and presents:

- lane name,
- status,
- suite counts where available,
- whether the real-backend lane ran or was skipped,
- links or references to the detailed checks and artifacts when needed.

This is the fastest path to the "at a glance" view the PR currently lacks.

### 3. Add real coverage measurement as a separate concern

Coverage should not be inferred from test reporters.
Measure coverage explicitly in CI:

- backend: `pytest --cov --cov-report=xml` plus machine-readable totals
- frontend: `vitest` coverage output with LCOV and machine-readable summary data

Then surface those results in GitHub-native summary and check output so the PR can answer:

- current total coverage,
- changed-scope regression status,
- whether overall coverage regressed.

### 4. Keep coverage reporting GitHub-native

Do not introduce an external coverage service.
Instead:

- generate backend and frontend coverage artifacts and totals in CI,
- keep a baseline from the default branch available to PR runs,
- compare PR coverage against the baseline inside GitHub Actions,
- publish the comparison result in job summaries and check output.

This keeps the signal inside GitHub while still measuring coverage and answering whether coverage regressed.

### 5. Defer reviewdog unless lint UX still feels insufficient

Reviewdog is a good fit for linter and typechecker diagnostics, but it does not solve the core "what was tested?" problem by itself.
Given the repo already emits annotations directly for lint and typecheck, this work should defer reviewdog and focus on summary plus coverage first.

## Deliverables

- Updated `.github/workflows/pr-ci.yml`
- Coverage measurement and comparison wiring in GitHub Actions
- Updated `docs/ci.md`
- A documented PR signal model that explains:
  - which check names correspond to which lanes,
  - where to look for suite details,
  - which coverage signals are gating vs informational,
  - how skipped optional lanes are represented

## Sequencing

### Phase 1: PR rollup summary

- Add a summary step or job that consolidates lane outcomes into one short table.
- Include explicit skipped/not-run messaging for optional lanes.
- Preserve current blocking behavior of the existing jobs.

### Phase 2: Coverage measurement and comparison

- Generate backend coverage XML in CI and extract machine-readable totals.
- Generate frontend coverage artifacts in CI and extract machine-readable totals.
- Make a default-branch baseline available so PR runs have something to compare against.
- Surface project coverage and regression results in PR summary and check output.

### Phase 3: Documentation and polish

- Update `docs/ci.md` with the new reporting model.
- Document how the default-branch coverage baseline is produced and consumed by PR runs.
- Document which signals are authoritative for reviewers.
- Reassess whether reviewdog adds enough value to justify follow-up work.

## Acceptance Criteria

- A reviewer can see, without opening raw logs, which test lanes ran and whether they passed.
- The PR surface shows measured backend and frontend coverage totals and whether coverage regressed.
- The PR surface shows whether changed-scope coverage regressed, even without an external coverage service.
- Optional lanes that did not run are labeled clearly as skipped or disabled rather than silently absent.
- Existing per-suite test reports continue to work.
- `docs/ci.md` matches the implemented behavior.

## Worker Notes

- Start from the current `dorny/test-reporter` setup; do not replace it unless there is a hard blocker.
- Treat coverage as the main net-new capability.
- Keep the implementation GitHub-native; no Codecov or similar hosted service.
- Keep check names stable where possible so branch protection does not drift unnecessarily.
