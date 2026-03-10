# Floor Plan Agent State Persistence Findings

## Summary

Floor-plan intake now runs as a first-class agent (`floor_plan_intake`) with typed deps and state.
State is attached through AG-UI routes and includes `thread_id`/`run_id` per request.

## Current Runtime Shape

1. AG-UI route
   - `POST /ag-ui/agents/{agent_name}` resolves one agent and one typed deps instance.
   - Route updates `deps.state.thread_id` and `deps.state.run_id` before dispatch.
2. Agent-local state
   - Floor-plan agent uses `FloorPlanIntakeAgentState`.
   - Search agent uses `SearchAgentState` (includes room snapshot context).
   - Image-analysis agent uses `ImageAnalysisAgentState`.
3. Tool persistence
   - Floor-plan toolset persists revisions through `FloorPlanRepository` and keeps in-memory scene cache in `FloorPlanSceneStore`.

## Result

- Follow-up floor-plan turns retain thread-scoped revision history.
- Rendered revisions can be confirmed via `confirm_floor_plan_revision`.
- State wiring is shared via AG-UI deps rather than graph-node state hydration.

## Deferred Follow-ups

- Introduce explicit per-agent persistence policy docs (`state_per_thread`, `data_per_turn`, `disabled`) for all agents.
- Define concurrency semantics for simultaneous runs on the same thread.
