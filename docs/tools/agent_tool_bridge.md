# Agent Tool Bridge Pattern

## Purpose
The tools package separates domain logic from runtime-specific decorators.

- Domain logic lives in plain Python classes implementing `ToolProtocol`.
- The bridge layer registers decorated callables on an agent runtime.
- The return shape is standardized via `ToolExecutionResult`.

## Current Bridge
`tal_maria_ikea.tools.floor_planner_tool.register_floor_planner_tool` uses duck typing:

- Expects an agent object with a callable `.tool` decorator.
- Registers `render_floor_plan(request: FloorPlanRequest)`.
- Delegates execution to `FloorPlannerTool.run`.

This keeps tools independent from one specific runtime package while still supporting pydantic-ai-style decoration.

## Why This Shape
- Testability: domain tool tests do not require agent runtime setup.
- Typing: request/response contracts are explicit and reusable.
- Extensibility: future tools can reuse the same result envelope and registration pattern.
