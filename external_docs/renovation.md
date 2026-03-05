# Renovation (Floor Planner Library)

Source:
- https://github.com/Nikolay-Lysenko/renovation
- Demo config:
  https://github.com/Nikolay-Lysenko/renovation/blob/master/docs/demo_configs/simple_floor_plan.yml

## Integration Notes
- Renovation accepts a YAML-like dictionary schema with top-level keys:
  - `project`
  - `default_layout`
  - `reusable_elements`
  - `floor_plans`
- Elements are declared with `type` and typed fields, then instantiated via the registry.
- Programmatic flow mirrors `renovation.__main__`:
  1. build registry (`create_elements_registry`)
  2. build `FloorPlan` objects
  3. add elements
  4. render via `Project(...).render_to_png(...)`

## Why We Wrap It
- We need strict typed validation before invoking renderer.
- We need stable tool output contracts for agent workflows.
