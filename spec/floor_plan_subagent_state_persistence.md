# Floor Plan Subagent State Persistence Findings

## Trace Context

- Trace file: `data/traces/copilotkit-events-1773145665741.json`
- Commit recorded in local manifest:
  - `68c1f015d29c573c0cfe3a054dd1fa49109e643d`
  - `data/trace_files_by_commit.jsonl`

## Validation: State Is Not Persisted Across Subagent Turns

The floor plan subagent currently behaves as stateless across turns from the AG-UI route.

Observed and code-level evidence:

1. Trace only shows run/text lifecycle events.
   - Event types present are `RUN_STARTED`, `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `RUN_FINISHED`.
   - No tool/state events are present in this trace.
2. Subagent runtime creates fresh graph state every turn.
   - `SubgraphAgent.run_one_turn()` calls `state=cls.build_state()` for each execution.
   - `FloorPlannerSubgraphAgent.build_state()` returns `FloorPlanIntakeState()`.
3. Subagent AG-UI handler is invoked with `deps=None`.
   - Route `POST /ag-ui/subagents/{subagent_name}` calls `handle_ag_ui_request(..., deps=None, ...)`.
   - This prevents sharing `ChatAgentState` with subagents.
4. Internal graph state mutation exists but is ephemeral.
   - Nodes mutate `ctx.state` (`_ingest_payload_heuristic`, `_apply_decision_updates`, render revision updates).
   - Those mutations are lost after the turn completes.

## Proposed State Shape

Define a typed per-thread state for `floor_plan_intake`, for example:

- `version: Literal["v1"]`
- `room_type: RoomType`
- `length_cm: float | None`
- `depth_cm: float | None`
- `wall_height_cm: float | None`
- `orientation_context_collected: bool`
- `fixed_constraints: list[str]`
- `question_rounds: int`
- `scene_revision: int`
- `current_scene: FloorPlanScene | None`
- `last_render: FloorPlanRenderOutput | None`

And hold this in shared AG-UI state keyed by subagent name and thread.

## Base Runtime Direction (Implemented)

- Subagent persistence is a base `SubgraphAgent` capability.
- Default mode persists typed state per thread per subagent.
- Turn history is captured per turn with:
  - user message
  - assistant message
  - output payload
  - optional notes list for key details that do not fit typed state
- Policy is configurable per subagent:
  - `state_per_thread`
  - `data_per_turn`
  - `disabled`

## Where State Should Be Updated

1. Subagent AG-UI route wiring:
   - In `src/ikea_agent/chat_app/main.py`, pass deps into subagent `handle_ag_ui_request` instead of `deps=None`.
2. Subagent execution lifecycle:
   - In `src/ikea_agent/chat/subagents/base.py`, hydrate state before `graph.run`.
   - Persist mutated state after `graph.run`.
3. Floor plan subagent mapping helpers:
   - In `src/ikea_agent/chat/subagents/floor_plan_intake/agent.py` (or a dedicated mapper module), add:
     - state model conversion from shared state -> `FloorPlanIntakeState`
     - `FloorPlanIntakeState` -> shared state serialization.
4. UI state payload for subagent page:
   - In `ui/src/app/subagents/[agent]/page.tsx`, include `thread_id` when calling `agent.setState(...)` so backend persistence can scope by thread.

## Expected Result

After these changes:

- The subagent can carry dimension/orientation/constraints and render revision across turns.
- Follow-up user messages should not re-trigger repeated basic intake questions when data is already known.
- Trace logs should show behavior consistent with accumulated floor-plan context per thread.

## Deferred TODOs

- Concurrency semantics are not addressed yet (for now, behavior is effectively last-write-wins).
- Future map-reduce/fan-out patterns need explicit reconciliation policy:
  - map stage should avoid mutating shared state
  - reduce stage should own final merge + state mutation.
