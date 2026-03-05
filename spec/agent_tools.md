# Agent Tools Spec

This document describes the agent-facing tools we want available in this repo, and the engineering constraints for implementing them.

## Principles

- Prefer tools that are thin adapters over proven libraries.
- Use Pydantic for tool argument validation and stable schemas.
- Use pydantic-ai’s tool system (`@agent.tool` / `@agent.tool_plain`) directly rather than inventing a parallel tool runtime.
- Avoid re-implementing rendering, geometry, or validation that the underlying library already provides.
- Tool functions should be idempotent where possible and avoid mutating input payloads.

---

## Floor Planner Tool (Renovation)

### Intent

Render a simple floor plan image (PNG) that the agent can show to the user to confirm room geometry (shape, doors, windows) before continuing with IKEA planning. The agent should use the image as a checkpoint:

- “Is this floor plan accurate?”
- “What’s wrong: dimensions, orientation, door/window positions?”

If the user corrects details, the agent updates the plan and re-renders.

### Units: Centimeters Only (Agent-Facing)

All agent-facing models in this repo use **centimeters** as **floats**.

- Example: `1.5` means 1.5 cm.
- We do not accept meters in tool inputs.
- Conversion boundary:
  - We convert from centimeters to meters (`m = cm / 100`) only at the renderer boundary when calling `renovation`.

Rationale:

- Users describe rooms in cm frequently, and IKEA product dimensions are typically cm.
- Keeping a single unit system avoids downstream confusion and repeated conversions in prompts/tools.

### Key Decision: Pydantic Wrappers Over Renovation Inputs/Outputs

Agents should never deal with YAML or untyped dicts.

We will wrap Renovation’s “settings dict” schema in a set of Pydantic models so that:

- tool call arguments are fully type-safe and self-documenting
- validation errors become “retryable” tool call errors in pydantic-ai
- we can add a small amount of helpful validation (without re-implementing geometry)

Internally, the renderer converts these Pydantic models into the exact dict shape Renovation expects (in meters), then calls Renovation.

We will treat `renovation` as the source of truth for:

- the underlying settings schema (as implemented in `renovation.__main__`)
- which elements exist and which fields they accept
- rendering behavior and output naming conventions

We should not build a parallel “room geometry” domain model (wall segments with start/end points, intersection checks, etc.). The tool input should mirror Renovation’s element primitives (walls/doors/windows/etc.) but with strong typing and unit conversion.

Rationale:

- The original spec said “the package expects floor plan data to be input in a certain way”.
- Renovation already defines this “certain way” as a YAML/dict settings structure and a registry of element constructors.
- pydantic-ai already provides typed tool arguments; we should lean on that rather than writing bespoke validators.

### Renovation Render Flow (Library Truth)

Renovation’s CLI (`python -m renovation -c config.yml`) does:

1. `yaml.load(..., Loader=yaml.FullLoader)` to get `settings: dict`
2. `create_elements_registry()` to map `type -> element class`
3. for each floor plan in `settings["floor_plans"]`:
   - create `FloorPlan(**layout)`
   - add title
   - add inherited reusable elements
   - add inline elements
4. `Project(floor_plans, dpi).render_to_png(png_dir)` (and/or PDF)

Our tool should follow this structure closely, but:

- do not parse YAML in the tool path (agent never provides YAML)
- avoid mutating the request payload (renovation’s CLI uses `.pop('type')` in one branch; we should not)

### Tool API

#### Tool name

`render_floor_plan`

#### Tool argument model

One Pydantic model parameter (this is important because pydantic-ai will simplify tool JSON schema when the only parameter is a `BaseModel`).

`FloorPlannerInput` should contain:

- `elements`: typed Renovation element wrappers (discriminated union by `type`)
- `layout_padding_cm`: optional padding used to infer layout bounds from elements (defaulted)
- `include_image_bytes`: optional boolean (default false) to return a pydantic-ai `ToolReturn` with `BinaryContent(image/png)` so the model can reason visually without a second fetch path

Notes:

- The tool must enforce that output path is under a repo-controlled artifacts directory (no arbitrary write locations).
- The tool must not require the agent to provide a “raw dict” settings object.
- The tool must not mutate the input model instances.
- The tool should avoid exposing rendering knobs that do not materially help the agent choose furniture/layout (for example `dpi`, title font, output filename).

#### Tool return type

Prefer a typed return model, e.g.:

- `output_png_path: str` (relative path)
- `rendered_title: str | None` (the plan title renovation used for the intermediate file)
- `element_counts: { walls: int, doors: int, windows: int, ... }` (best-effort)
- `warnings: list[str]`

If `include_image_bytes=true`, return `ToolReturn` with:

- `return_value` set to the typed return model (or a JSON-serializable dict)
- `content` including the PNG bytes (`BinaryContent`)
- `metadata` including the output path and relevant counts

### pydantic-ai Registration Pattern

Use pydantic-ai directly:

- If the tool does not need dependencies, use `@agent.tool_plain`.
- If the tool needs dependencies (e.g. an output root directory from settings), use `@agent.tool` and accept `ctx: RunContext[Deps]` first.

Example shape:

```python
from pydantic_ai import Agent, ToolReturn, BinaryContent

@agent.tool_plain
def render_floor_plan(payload: FloorPlannerInput) -> FloorPlannerOutput | ToolReturn:
    ...
```

### Pydantic Wrappers (Dev Spec)

We model a Renovation-like structure, but in Pydantic and centimeters.

Recommended approach:

- A root `RenovationPlan` model that contains:
  - `elements`: list of discriminated-union element models
- Layout is inferred automatically from element extents plus configurable padding.
- Element union is discriminated by `type`:
  - `WallElement(type="wall", anchor_point_cm=(x, y), length_cm=..., thickness_cm=..., orientation_angle_deg=..., color=...)`
  - `DoorElement(type="door", anchor_point_cm=(x, y), doorway_width_cm=..., door_width_cm=..., thickness_cm=..., orientation_angle_deg=..., to_the_right=..., color=...)`
  - `WindowElement(type="window", anchor_point_cm=(x, y), length_cm=..., overall_thickness_cm=..., single_line_thickness_cm=..., orientation_angle_deg=...)`
  - Additional Renovation elements may be added later as needed (dimension arrows, polygons, text boxes, lighting).

Conversion:

- Each wrapper model exposes `to_renovation_kwargs_m()` producing Renovation kwargs in **meters** for all distance-like fields.
- The renderer builds Renovation’s in-memory objects (via element registry) without ever parsing YAML.

Helpful validators (low risk, high leverage):

- Positive checks: `length_cm > 0`, `thickness_cm > 0`, etc.
- Layout sanity: `top_right_corner_cm.x > bottom_left_corner_cm.x` and same for y.
- Door sanity: `door_width_cm <= doorway_width_cm` (if both provided).
- Element `type` must match a known Renovation registry key (enforced at runtime by checking `create_elements_registry()`), with an actionable error when unsupported.

### Agent Flows (When and How It Should Be Called)

#### Flow 1: Basic rectangular room

- User: “My room is 3.4m by 2.6m. Door on the left wall, window on the right wall.”
- Agent:
  - builds a `RenovationPlan` in cm for a single plan with 4 wall elements + door + window
  - calls `render_floor_plan`
  - shows the PNG
  - asks user to confirm/correct

#### Flow 2: Complex boundary (recessed/alcove)

- User: “The room has a recess near the top-right corner; the top wall steps in by 0.2m for 0.7m.”
- Agent:
  - represents this as additional wall elements (as renovation expects), in cm
  - calls `render_floor_plan`
  - asks: “Is the recess placement and size correct?”

#### Flow 3: Revision loop

- User: “Door is actually 0.8m from the bottom, not at the corner.”
- Agent:
  - updates only the relevant door element’s `anchor_point_cm` (and orientation if needed)
  - re-renders, compares output visually, asks for confirmation

#### Flow 4: Visual reasoning upstream

- Agent calls `render_floor_plan(include_image_bytes=true)`
- Tool returns a `ToolReturn` containing the PNG bytes
- Agent uses the image content to reason about layout conflicts (and optionally to share with a UI)

### Existing Tests We Have Today (Intent to Preserve)

The current test suite for the floor planner asserts:

- a YAML fixture can be parsed into a typed request model
- invalid geometry-like cases are rejected early (e.g. self-intersections, open polygon, opening outside wall)
- rendering produces a non-empty PNG with a stable filename
- a tool wrapper can be registered on an agent

We should preserve the spirit (typed inputs, stable artifacts, predictable errors) while deleting the geometry-specific logic and removing YAML from agent-facing inputs.

### New Test Spec (After Migration)

Tests should validate the new contract:

- `FloorPlannerInput` validates typed element payloads (element `type`, name uniqueness, required fields per element kind).
- Rendering produces a PNG in `artifacts/floor_plans/` with a stable default filename (`floor_plan.png`).
- Rendering does not mutate the input Pydantic objects (idempotency).
- Invalid settings produce actionable errors (ideally Pydantic validation errors before render, otherwise a renderer exception wrapped into a tool error).
- Optional: `include_image_bytes=true` returns a `ToolReturn` whose content includes a PNG `BinaryContent`.

Fixtures:

- Keep a small “simple floor plan” fixture modeled after renovation’s demo config but expressed as our Pydantic wrapper (cm-based).
- Keep one “complex boundary” fixture with multiple walls.

### Migration Plan (Delete the Current Custom Tool)

1. Remove the current floor planner “geometry” request models and conversion code.
   - Replace legacy geometry modules with wrappers under `src/ikea_agent/tools/floorplanner/` and migrate tests/fixtures that encode the old schema.
2. Replace with a typed model that mirrors renovation’s config/settings structure.
   - Keep it intentionally shallow: validate types and required keys, avoid custom geometric reasoning.
   - Use centimeters in all models; convert to meters only at render boundary.
3. Implement a renderer that is a near-direct port of `renovation.__main__`, with:
   - no YAML parsing in the tool path (agent never provides YAML)
   - no mutation of settings dict
   - stable output path and file naming
4. Implement the pydantic-ai tool function using `@agent.tool_plain` and a single `BaseModel` payload argument.
5. Update tests to match the new fixtures and contract.
6. Update `external_docs/renovation.md` and add a small `external_docs/pydantic_ai_tools.md` capturing the tool patterns we rely on.
