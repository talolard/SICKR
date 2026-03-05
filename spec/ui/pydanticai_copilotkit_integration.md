# Spec: PydanticAI + CopilotKit Integration

## Goal

Provide a production-ready path to replace or augment the built-in pydantic-ai web UI with CopilotKit while preserving current `ikea_agent` graph/tool behavior.

## Architecture

### Backend (Python)

1. Keep `ikea_agent` FastAPI runtime as the source of truth for agent logic.
2. Expose agent via AG-UI compatible endpoint (`agent.to_ag_ui(...)`).
3. Keep retrieval tool contract typed (`list[ShortRetrievalResult]`).
4. Add image-aware tools:
   - `analyze_uploaded_image(image_ref: str, prompt: str) -> ImageAnalysisResult`
   - `search_with_image_context(image_ref: str, user_query: str) -> list[ShortRetrievalResult]`

### UI (CopilotKit + Next.js)

1. Add CopilotKit runtime route (`/api/copilotkit`) with `HttpAgent` to Python backend.
2. Use `CopilotChat` / Agentic chat components to render:
   - assistant/user messages
   - tool call status and outputs
   - structured product lists/cards
3. Add image upload widget in composer:
   - uploads to app storage endpoint
   - inserts attachment reference into agent message context
4. Add image message renderer:
   - render returned image URLs or data refs inline in conversation timeline.

## Contracts

### Message Payload Extensions

- `attachments: list[AttachmentRef]` on user turns
- `tool_outputs: list[ToolOutputView]` on assistant/tool turns

### Image Types

- `AttachmentRef`:
  - `attachment_id: str`
  - `mime_type: str`
  - `uri: str`
  - `width: int | None`
  - `height: int | None`

- `ImageToolOutput`:
  - `caption: str`
  - `images: list[AttachmentRef]`

## Run Flow

1. User uploads image and enters query.
2. UI posts message + attachment refs to CopilotKit runtime.
3. Runtime forwards request to AG-UI-backed PydanticAI agent.
4. Agent calls retrieval/image tools as needed.
5. Tool events stream to UI and render progressively.
6. Final assistant message includes product recommendations + optional image outputs.

## MVP Milestones

1. Wire CopilotKit runtime to existing agent endpoint.
2. Render tool calls and current text responses.
3. Add image upload and attachment passthrough.
4. Add image output renderer.
5. Add session/thread persistence wiring.

## Testing

1. Integration test: tool call events stream and render in UI.
2. Integration test: image upload attachment reaches backend tool.
3. Integration test: image output payload renders in chat timeline.
4. Regression test: text-only retrieval flow unchanged.

## Operational Notes

- Keep model/provider choices configurable via Python env settings.
- Keep typed schemas for all tool payloads and attachment metadata.
- Keep CopilotKit UI as a client layer; business logic remains in `ikea_agent` backend.
