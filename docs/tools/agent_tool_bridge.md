# Agent Tool Bridge Pattern

## Purpose
Tools are exposed directly in the active chat agent runtime.

- Domain logic lives in `ikea_agent.tools.<tool_name>`.
- Registration is grouped under `src/ikea_agent/chat/tools/` modules and wired from
  `src/ikea_agent/chat/agent.py`.
- Return shapes are typed Pydantic models (and optionally `ToolReturn` for binary content).

## Current Pattern
`build_chat_agent` registers grouped tool registries:

- `register_search_context_tools(...)`
- `register_floor_plan_tools(...)`
- `register_image_analysis_tools(...)`

`render_floor_plan` delegates to `ikea_agent.tools.floorplanner.tool.render_floor_plan`.
The floor planner path also uses a per-thread scene store in chat deps:
- load current scene/revision
- apply full-scene or incremental changes
- render `SVG + PNG`
- persist updated scene state and revision

Return payload includes stable UI/render metadata:
- `images` attachment refs (SVG/PNG)
- `scene_revision`
- `scene_level`
- `warnings`
- `legend_items`
- `scene_summary`
- `scene`

Image analysis tools delegate to `ikea_agent.tools.image_analysis.tool`.

`run_search_graph` returns a structured `SearchGraphToolResult`:

- `results`: MMR-selected list of `ShortRetrievalResult`
- `total_candidates`: candidate count before MMR selection
- `returned_count`: count after MMR selection + limit
- `warning`: optional `SearchResultDiversityWarning` when selected output is concentrated

The tool also accepts an optional `candidate_pool_limit` argument so the model can expand
retrieval depth before MMR selection when search is too narrow.

`list_room_3d_snapshot_context` returns a merged payload:
- `state_snapshots`: UI-provided `room_3d_snapshots` from AG-UI shared state
- `persisted_snapshots`: durable thread-scoped snapshot metadata from persistence
- `state_count` / `persisted_count`: stable summary counters for prompt/tool reasoning

## Why This Shape
- Testability: tool function behavior is tested independently from model/provider wiring.
- Typing: request/response contracts are explicit Pydantic models.
- Clarity: avoids extra protocol/bridge layers for this runtime.
