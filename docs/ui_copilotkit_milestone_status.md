# CopilotKit + AG-UI milestone status

Updated: 2026-03-05

## Completed milestones

- Milestone -1: TypeScript UI workspace + test infrastructure (`ui/` Next.js, Vitest, Playwright, mock AG-UI SSE).
- Milestone 0: real AG-UI wiring (`/ag-ui` mount in FastAPI, `/api/copilotkit` runtime route, real-backend smoke path).
- Milestone 1: tool-call lifecycle visibility and product-card rendering.
- Milestone 2: image attachment upload endpoint, attachment composer, send-blocking while upload pending, retry-send with attachment refs.
- Milestone 3: generated image artifact output (`ImageToolOutput`) and inline image viewer modal.
- Milestone 4: long-running progress updates + run-level status container + local cancellation UX.
- Milestone 5: thread/session persistence, URL thread routing, resume-on-refresh, thread isolation.

## Key commands

- Start backend: `make chat`
- Start UI (real backend): `make ui-dev-real`
- Start UI (mock): `make ui-dev-mock`
- UI unit tests: `make ui-test`
- UI mock E2E: `make ui-test-e2e`
- UI real-backend smoke E2E: `make ui-test-e2e-real`
