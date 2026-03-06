# CopilotKit + AG-UI milestone status

Updated: 2026-03-06

## Completed milestones

- Milestone -1: TypeScript UI workspace + test infrastructure (`ui/` Next.js, Vitest, Playwright, mock AG-UI SSE).
- Milestone 0: real AG-UI wiring (`/ag-ui` mount in FastAPI, `/api/copilotkit` runtime route, real-backend smoke path).
- Milestone 1: tool-call lifecycle visibility and product-card rendering.
- Milestone 2: image attachment upload endpoint, attachment composer, send-blocking while upload pending, retry-send with attachment refs.
- Milestone 3: generated image artifact output (`ImageToolOutput`) and inline image viewer modal.
- Milestone 4: long-running progress updates + run-level status container + local cancellation UX.
- Milestone 5: thread/session persistence, URL thread routing, resume-on-refresh, thread isolation.

## Temporary thread fallback behavior

- Main UI now keeps a stable thread id in URL (`?thread=...`) and localStorage, and passes it to `CopilotKit`.
- Agent shared state uses `session_id == thread_id` so backend runs are aligned to selected thread.
- Thread picker allows selecting existing thread ids or creating a new one.
- Temporary limitation while backend persistence is disabled:
  - selecting a thread that cannot be resumed from backend session state shows a warning
  - UI automatically starts a new thread instead of failing
  - this warning is expected until backend thread persistence is implemented

## Key commands

- Start backend: `make chat`
- Start UI (real backend): `make ui-dev-real`
- Start UI (mock): `make ui-dev-mock`
- UI unit tests: `make ui-test`
- UI mock E2E: `make ui-test-e2e`
- UI real-backend smoke E2E: `make ui-test-e2e-real`
