# Floor Planner Tool

## Summary
The floor planner tool renders a room plan to a local PNG using `renovation`.

Code locations:
- `src/ikea_agent/tools/floorplanner/models.py`
- `src/ikea_agent/tools/floorplanner/renderer.py`
- `src/ikea_agent/tools/floorplanner/tool.py`

## Input Contract
`FloorPlanRequest` is the canonical typed payload.

Core concepts:
- All user/agent units are centimeters as floats.
- Layout and Renovation element wrappers are validated with Pydantic.
- Conversion to meters happens only at the Renovation render boundary.

## Rendering Behavior
- Tool writes PNG artifacts to local filesystem (`artifacts/floor_plans` by default).
- Output file is written as `floor_plan.png`.
- Tool returns typed output (`FloorPlannerToolResult`) and can optionally return `ToolReturn` with PNG `BinaryContent`.

## Agent Usage Guidance
Use floor planning when the user provides clear room dimensions/openings.
After rendering, ask for confirmation before continuing, e.g.:
- Is the room shape and opening placement correct?
- How confident are you that this matches the real room?

## Sample Data
Representative payloads and checks are in:
- `tests/tools/test_floor_planner_models.py`
- `tests/tools/test_floor_planner_renderer.py`
- `tests/tools/test_floor_planner_tool.py`

## Artifact Policy
Generated images are runtime/test artifacts and are not committed to git.
