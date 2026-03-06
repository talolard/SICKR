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
- Milestone 6: persistent floor-plan preview panel beside chat, fed by `render_floor_plan` tool outputs
  with per-thread local persistence in UI state.
- Milestone 7: 2D/3D floor-plan tabs with React Three Fiber room scene, OpenUSD ingest support,
  and PNG snapshot capture wired into typed agent state + persistence APIs.

## Floor-plan preview reliability note

- Floor-plan preview updates are propagated in two paths:
  - direct callback from tool renderer (`onFloorPlanRendered`)
  - browser event bridge (`ikea-floorplan-rendered`) consumed by `ui/src/app/page.tsx`
- The event bridge exists to keep preview updates robust across AG-UI replay/rerender timing,
  where render callbacks can be deferred or replayed.
- Shared bridge helpers live in `ui/src/lib/floorPlanPreviewEvents.ts`.

## 3D Snapshot Flow

- The 3D tab exposes `Capture PNG` from the current camera perspective.
- Capture payload includes:
  - PNG snapshot image
  - camera metadata (`position_m`, `target_m`, `fov_deg`)
  - lighting metadata (fixture ids + emphasized count)
  - optional user comment
- UI uploads snapshot images through `/api/attachments`, persists metadata through
  `/api/room-3d/snapshots`, and writes `room_3d_snapshots` into AG-UI shared state.
- Agent-side retrieval is explicit via `list_room_3d_snapshot_context`.

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
