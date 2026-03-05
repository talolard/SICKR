# Renovation (Floor Planner Library)

Source:
- https://github.com/Nikolay-Lysenko/renovation
- Demo config:
  https://github.com/Nikolay-Lysenko/renovation/blob/master/docs/demo_configs/simple_floor_plan.yml

## Integration Notes
- Renovation accepts a YAML/dict "settings" schema with top-level keys:
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

## What Renovation Actually Exposes

The installed package is intentionally small:

- `renovation.elements.create_elements_registry()` returns `{type_str: ElementClass}`
- `renovation.floor_plan.FloorPlan(...)` holds a matplotlib figure and supports:
  - `.add_title(text=..., font_size=..., ...)`
  - `.add_element(Element(...))`
- `renovation.project.Project(floor_plans, dpi)` supports:
  - `.render_to_png(output_dir)` (writes one PNG per plan)
  - `.render_to_pdf(output_path)`

## Settings Parse + Render (Truth Source)

The CLI (`python -m renovation -c config.yml`) loads a dict via `yaml.load(..., Loader=yaml.FullLoader)` and then:

- merges `default_layout` into each plan if plan `layout` is omitted
- instantiates elements from `reusable_elements` and `floor_plans[].elements`
- renders to `project.png_dir` and/or `project.pdf_file`

Implementation footguns if we re-use the CLI logic:

- The CLI mutates element dicts in one branch with `element_params.pop("type")`.
  A tool wrapper should avoid mutating the request payload to keep tool calls idempotent.
- Prefer `yaml.safe_load` for any YAML parsing we do outside the library.
