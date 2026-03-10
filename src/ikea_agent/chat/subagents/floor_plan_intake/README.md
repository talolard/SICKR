# Floor Plan Intake Subagent

Collect enough room constraints to create an initial floor-plan draft, then iterate with user corrections until the user is satisfied or wants to stop.

## Runtime shape

- Implemented as a plain `pydantic_ai.Agent` (no `pydantic_graph` layer).
- Uses prompt instructions from `prompt.md`.
- Uses shared chat tool contracts so CopilotKit can render tool outputs directly.

## Tools used

- `render_floor_plan`
- `load_floor_plan_scene_yaml`
- `export_floor_plan_scene_yaml`
- `confirm_floor_plan_revision`

## Behavior expectations

- Ask for approximate dimensions and fixed architectural constraints.
- Assume 280 cm height if omitted and explicitly tell the user.
- Call `render_floor_plan` for draft generation and corrections.
- Keep iterating until the user confirms, then call `confirm_floor_plan_revision`.
