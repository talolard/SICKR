# Agent Tool Bridge Pattern

## Purpose
Tools are exposed directly in the active chat agent module.

- Domain logic lives in `ikea_agent.tools.<tool_name>`.
- Registration happens in `src/ikea_agent/chat/agent.py` via `@agent.tool` / `@agent.tool_plain`.
- Return shapes are typed Pydantic models (and optionally `ToolReturn` for binary content).

## Current Pattern
`build_chat_agent` registers:

- `run_search_graph(...)` via `@agent.tool`
- `list_uploaded_images(...)` via `@agent.tool`
- `generate_floor_plan_preview_image()` via `@agent.tool_plain`
- `render_floor_plan(request: FloorPlanRequest)` via `@agent.tool_plain`
- `detect_objects_in_image(request: ObjectDetectionRequest)` via `@agent.tool`
- `estimate_depth_map(request: DepthEstimationRequest)` via `@agent.tool`
- `segment_image_with_prompt(request: SegmentationRequest)` via `@agent.tool`
- `analyze_room_photo(request: RoomPhotoAnalysisRequest)` via `@agent.tool`

`render_floor_plan` delegates to `ikea_agent.tools.floorplanner.tool.render_floor_plan`.
Image analysis tools delegate to `ikea_agent.tools.image_analysis.tool`.

## Why This Shape
- Testability: tool function behavior is tested independently from model/provider wiring.
- Typing: request/response contracts are explicit Pydantic models.
- Clarity: avoids extra protocol/bridge layers for this runtime.
