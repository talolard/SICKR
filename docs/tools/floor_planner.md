# Floor Planner Tool

## Summary
The floor planner tool renders a typed room scene to local `SVG + PNG` artifacts.
It supports architecture, doors/windows, furniture placements, electrical fixtures,
and vertical/elevation cues for stacked or wall-mounted items.

Code locations:
- `src/ikea_agent/tools/floorplanner/models.py`
- `src/ikea_agent/tools/floorplanner/renderer.py`
- `src/ikea_agent/tools/floorplanner/tool.py`
- `src/ikea_agent/tools/floorplanner/yaml_codec.py`
- `src/ikea_agent/tools/floorplanner/scene_store.py`

## Input Contract
`FloorPlanRenderRequest` is the canonical typed payload.

Core concepts:
- All user/agent units are centimeters as floats.
- Request can provide either:
  - a full scene (`scene`)
  - incremental changes (`changes`) to current per-thread scene state
- Scene levels:
  - `baseline`: architecture + placements
  - `detailed`: baseline + fixtures + tagged items
- Validation is schema-focused and cheap (high-leverage invariants only).
- Openings validation:
  - every door/window segment must lie on an existing wall segment
  - zero-length opening segments are rejected
- Optional labels are supported on walls/doors/windows and are surfaced in rendering and scene summaries.

## Rendering Behavior
- Tool writes deterministic artifacts under floor plan output dir:
  - `floor_plan.svg`
  - `floor_plan.png`
- Render includes top view and right-side X/Z elevation panel.
- Visual layers include architecture, openings, placements, fixtures, legend, and warnings.
- Tool returns typed `FloorPlanRenderOutput` and optionally `ToolReturn` with PNG `BinaryContent`.

## Agent Usage Guidance
Use floor planning when the user provides room dimensions/openings and object placement intent.
Default flow is baseline-first confirmation before detailed placement:
- Is the room shape and opening placement correct?
- How confident are you that this matches the real room?

Then proceed with incremental placement updates via `changes`.

## YAML Interop
- `load_floor_plan_scene_yaml(yaml_text, scene_level=...)` parses YAML into typed scene state.
- `export_floor_plan_scene_yaml()` exports current scene state as YAML.
- YAML is an interop/edit format; numeric truth remains in structured scene fields.

## Sample Data
Representative payloads and checks are in:
- `tests/tools/test_floor_planner_models.py`
- `tests/tools/test_floor_planner_renderer.py`
- `tests/tools/test_floor_planner_tool.py`
- `tests/tools/test_floor_planner_scene_store.py`

## Artifact Policy
Generated images are runtime/test artifacts and are not committed to git.
