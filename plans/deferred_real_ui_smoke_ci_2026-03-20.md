# Deferred Real UI Smoke CI Plan

## Goal

Move the expensive real-backend CopilotKit smoke out of the default local workflow, keep it as CI signal after the cheaper PR workflows succeed, and make the backend response deterministic so the smoke does not depend on an external LLM.

## Scope

- `.github/workflows/pr-ci.yml`
- `.github/workflows/e2e-real-ui-smoke.yml`
- `Makefile`
- `src/ikea_agent/config.py`
- `src/ikea_agent/chat/modeling.py`
- `ui/e2e/real-backend.spec.ts`
- supporting tests and workflow docs

## Design

1. Keep `PR CI` focused on fast blocking lanes:
   - backend
   - frontend unit
   - coverage
   - mock Playwright
2. Add a separate workflow triggered by upstream workflow completion:
   - wait for both `PR CI` and `Dependency Review` to succeed for the same PR SHA
   - then run the real-backend smoke against that exact PR head
3. Make the smoke deterministic:
   - add a settings-driven deterministic response override
   - have the smoke target start the backend with that override enabled
   - assert the exact deterministic assistant text in Playwright

## Expected outcome

- local iteration relies on `make tidy` plus targeted checks
- real-backend smoke remains available locally for debugging, but not as the default readiness gate
- CI still exercises the CopilotKit-to-AG-UI path, without using a paid or stochastic external model
