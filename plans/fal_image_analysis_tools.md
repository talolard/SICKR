# Plan: fal.ai Image Analysis Tooling

## Goal
Add typed image-analysis tools that operate on uploaded chat attachments so the agent can:

1. Detect objects in room photos.
2. Estimate depth for rough room structure.
3. Segment prompt-targeted regions (including multiple masks).
4. Run a combined room-photo understanding call for faster iteration.

## Scope
- New backend tool package at `src/ikea_agent/tools/image_analysis/`.
- Shared fal call/upload/download core reused by all tools.
- Agent registration in `src/ikea_agent/chat/agent.py`.
- CopilotKit renderers for each tool output class.
- Unit tests for model validation, tool orchestration, and UI renderers.
- Docs updates in `docs/` and `external_docs/`.

## Key Decisions
- Keep `FAI_AI_API_KEY` as supported env var and map it to `FAL_KEY` for `fal-client`.
- Use uploaded `AttachmentRef` inputs and store all generated artifacts in local attachment storage.
- Keep tool outputs typed and JSON-serializable with top-level `caption` + `images` for renderer compatibility.
- Provide both low-level tools and one combined high-level room-analysis tool.
