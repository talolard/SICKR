# SVG Floor Plan Engine Migration

## Goal
Replace the current renovation-backed floor-plan renderer with a typed in-repo SVG+PNG scene renderer that supports incremental placement updates, elevation cues for stacked/vertical items, and a large persistent preview panel beside chat.

## Scope
- Replace `render_floor_plan` contract in place with typed scene-based request/response models.
- Support both baseline and detailed scene levels using discriminated unions.
- Add thread-scoped in-memory scene state in backend (no durable persistence in this stream).
- Add YAML import/export helpers while keeping runtime contracts in Pydantic types.
- Return both SVG and PNG artifacts per render; include PNG binary content for vision-capable model use.
- Add UI panel that shows the latest rendered plan, centered and large next to chat.

## Out of Scope
- Durable cross-process persistence.
- Interactive drag/resize editing in UI.
- Heavy geometric validation (collision solvers, expensive overlap checks).
- 3D rendering pipeline.

## Acceptance Criteria
- Agent can iteratively add/update/remove placements through tool calls.
- User sees a stable, readable, large render next to chat after each update.
- Vertical/stacked distinctions are visible via elevation strip and labels.
- Tool returns typed warnings with severity for cheap validation checks.
- YAML can be imported into typed scene objects and exported back.

## References
- `spec/agent_tools.md`
- `spec/ui/pydanticai_copilotkit_integration.md`
- `docs/tools/floor_planner.md`
- `docs/tools/agent_tool_bridge.md`

