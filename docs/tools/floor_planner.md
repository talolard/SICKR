# Floor Planner Tool

## Summary
The floor planner tool renders a room plan to a local PNG using `renovation`.

Code locations:
- `src/tal_maria_ikea/tools/floor_planner_models.py`
- `src/tal_maria_ikea/tools/floor_planner_renderer.py`
- `src/tal_maria_ikea/tools/floor_planner_tool.py`

## Input Contract
`FloorPlanRequest` is the canonical typed payload.

Core concepts:
- Ordered perimeter walls (`walls`) that form a closed, non-self-intersecting polygon.
- Doors/windows are anchored to walls by `wall_id` + offset.
- Geometry validation rejects impossible layouts before rendering.

## Rendering Behavior
- Tool writes PNG artifacts to local filesystem (`artifacts/floor_plans` by default).
- Output file is renamed to `<output_filename_stem>.png`.
- Tool returns `ToolExecutionResult` with output path and summary metadata.

## Agent Usage Guidance
Use floor planning when the user provides clear room dimensions/openings.
After rendering, ask for confirmation before continuing, e.g.:
- Is the room shape and opening placement correct?
- How confident are you that this matches the real room?

## Sample Data
Fixtures are in `tests/fixtures/floor_planner/`.

Valid scenarios:
- `valid_room_complex.yaml` (recessed corner room)
- `valid_hallway_7m_x_2_5m.yaml` (7m x 2.5m hallway with doors)

Invalid scenarios:
- self-intersection
- opening outside wall extent
- negative dimensions
- open polygon perimeter

## Artifact Policy
Generated images are runtime/test artifacts and are not committed to git.
