# Floorplanner Hypothesis Tests + SVG Helper

## Goal
Increase confidence in the floorplanner tool by adding Hypothesis property tests that generate
plausible, renderer-friendly `FloorPlanRequest` payloads (axis-aligned rectangle, occasionally
with a single concave corner; optional doors/windows). Use these to validate request/settings
invariants and to run a small amount of renderer/tool smoke coverage.

## Approach
- Add `hypothesis` as a dev dependency.
- Add `FloorPlannerRenderer.render_svg(...)` that writes a stable `floor_plan.svg` artifact.
  - Keep the existing PNG tool contract unchanged.
- Add Hypothesis strategies in tests to generate:
  - closed axis-aligned wall boundaries (rectangle or 1-notch concave)
  - door/window elements placed along a selected wall with safe offsets and sizes
- Property tests:
  - `FloorPlanRequest.model_validate(payload)` succeeds for generated payloads
  - `to_renovation_settings(...)` is idempotent and uses meters
  - inferred layout bounds contain all element extent points
  - small-sample renderer/tool smoke runs produce non-empty PNG (and SVG via helper)

## Quality Gate
- `make format-all`
- `make test`
- `make tidy`

