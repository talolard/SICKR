# Agent Tool Bridge Pattern

## Purpose
The floor planner tool is exposed directly in the active chat agent module.

- Domain logic lives in `ikea_agent.tools.floorplanner`.
- Registration happens in `src/ikea_agent/chat/agent.py` via `@agent.tool_plain`.
- Return shape is typed (`FloorPlannerToolResult`) with optional rich `ToolReturn`.

## Current Pattern
`build_chat_agent` registers:

- `run_search_graph(...)` via `@agent.tool`
- `render_floor_plan(request: FloorPlanRequest)` via `@agent.tool_plain`

`render_floor_plan` delegates to `ikea_agent.tools.floorplanner.tool.render_floor_plan`.

## Why This Shape
- Testability: tool function behavior is tested independently from model/provider wiring.
- Typing: request/response contracts are explicit Pydantic models.
- Clarity: avoids extra protocol/bridge layers for this runtime.
