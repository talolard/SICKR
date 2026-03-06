# T7I Plan: 3D Room View, OpenUSD, Snapshot-to-Agent

## Context
Epic `tal_maria_ikea-t7i` adds a full 2D/3D floor-plan workflow, OpenUSD ingest, and a typed snapshot context channel from UI to backend agent tools.

## Scope
- Extend floor-plan preview tool contract in UI to persist typed `scene` + `scene_summary`.
- Add tabbed 2D/3D preview with React Three Fiber scene rendering.
- Add 3D snapshot capture UX, optional comment, and attachment integration.
- Add durable persistence tables/repositories for room 3D assets and snapshots.
- Add OpenUSD ingest validation for `.usda/.usd/.usdc/.usdz`.
- Expose typed backend and Next.js proxy APIs for room 3D assets/snapshots.
- Extend `ChatAgentState` with snapshot context and add retrieval tool.
- Add tests/docs for the integrated flow.

## Sequencing
1. `t7i.1`: UI contract extension (`scene`, `scene_summary`) + tests.
2. `t7i.2`: 2D/3D tab UI and typed R3F renderer.
3. `t7i.3`: snapshot capture UX + comment + agent state propagation.
4. `t7i.4`: migration, models, repositories for room 3D assets/snapshots.
5. `t7i.5`: OpenUSD validation/ingest service and API wiring.
6. `t7i.6`: FastAPI + Next.js proxy routes for room 3D APIs.
7. `t7i.7`: agent state/tool contract for snapshot retrieval.
8. `t7i.8`: broaden tests/docs and run quality gates.

## Constraints
- Keep current 2D preview and existing attachment flow backward compatible.
- Prefer typed request/response models and small composable repository/services.
- Ensure idempotent UI rendering keyed by tool-call context where applicable.
