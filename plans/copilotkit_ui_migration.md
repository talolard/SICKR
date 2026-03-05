# CopilotKit UI Migration (PydanticAI AG-UI)

## Context

We currently have:

- A working CopilotKit runtime endpoint in Next.js: `ui/src/app/api/copilotkit/route.ts` (bridges to Python via `HttpAgent`).
- A custom “AG-UI Streaming Harness” UI at `ui/src/app/page.tsx` that manually parses SSE and renders tool calls/results via bespoke components.

The harness is useful for low-level debugging, but it is **not** CopilotKit’s intended UI integration path and produces the “ugly tool blocks” experience.

The CopilotKit PydanticAI quickstart expects:

- Wrap the UI in a `CopilotKit` provider (`@copilotkit/react-core`) at the app root.
- Use prebuilt components (`CopilotSidebar` / `CopilotChat`) and hook-based tool rendering (`useRenderTool`, `useDefaultRenderTool`) from `@copilotkit/react-core/v2`.

## “Where We Deviated” (Concrete)

1. **Missing provider wiring**
   - We do not wrap the Next.js `RootLayout` with `<CopilotKit runtimeUrl="/api/copilotkit" agent="...">`.
2. **Missing CopilotKit UI dependencies**
   - `ui/package.json` includes `@copilotkit/runtime` but does **not** include `@copilotkit/react-core` or `@copilotkit/react-ui`.
3. **Custom chat loop**
   - `ui/src/app/page.tsx` uses `/api/agui-run` and an ad-hoc event schema instead of using CopilotKit’s runtime + UI components.
4. **Tool rendering happens “out of band”**
   - We render tool calls from our custom event store instead of registering renderers with CopilotKit hooks.
5. **Image URIs are not safely routable**
   - Backend `AttachmentRef.uri` is relative (`/attachments/{id}`), but UI runs on a different origin/port (Next `:3000` vs Python `:8000`).

## Target UX

1. CopilotKit-native chat UI (sidebar or embedded chat) with streaming assistant output.
2. Tool calls render via `useRenderTool` (per-tool) and `useDefaultRenderTool` (fallback), not as raw JSON blocks.
3. Attach images in the chat:
   - Upload(s) show progress + retry/remove.
   - On send, the agent run receives attachment refs in structured state.
4. Agent can *show* images:
   - Tools return a typed `ImageToolOutput` with `AttachmentRef`s.
   - UI renders these images with a dedicated renderer (grid + modal viewer).

## Decisions (Recommended Defaults)

- **Keep Next.js**: CopilotKit’s “natural” integration path is Next.js + runtime route; removing Next would force a custom Node server anyway and diverge from upstream patterns.
- **Use CopilotKit v2 React APIs**: `@copilotkit/react-core/v2` for `CopilotSidebar`, `useRenderTool`, `useDefaultRenderTool`, `useAgent`, `useCopilotKit`.
- **Use shared agent state for attachments**:
  - Frontend: `agent.setState({ attachments: AttachmentRef[] })`.
  - Backend: deps implements `StateHandler` by containing a `state: AgentState` field.

## Implementation Plan (Incremental)

### Milestone 1: Replace Harness UI With CopilotKit Provider + Sidebar

**Frontend**

- Add dependencies:
  - `@copilotkit/react-core`
  - `@copilotkit/react-ui`
- In `ui/src/app/layout.tsx`:
  - Import `@copilotkit/react-ui/v2/styles.css`.
  - Wrap `{children}` with:
    - `<CopilotKit runtimeUrl="/api/copilotkit" agent="ikea_agent">...</CopilotKit>`
- Replace `ui/src/app/page.tsx` with a small app shell that mounts `CopilotSidebar` (and optionally a normal page UI around it).
- Keep the existing harness as a separate route, e.g. `/debug/agui-harness`, for low-level debugging.

**Backend**

- No changes required (AG-UI is already mounted at `/ag-ui`).

**Acceptance**

- Chat works with streaming text using the CopilotKit UI.
- Tool calls appear as tool call entries (even if default-rendered initially).

### Milestone 2: Tool Rendering Via Hooks

**Frontend**

- Create a single registry component, e.g. `ui/src/copilotkit/toolRenderers.tsx`, that registers:
  - `useDefaultRenderTool({ render: ... })` fallback.
  - `useRenderTool({ name: "run_search_graph", render: ... })` custom renderer.
  - `useRenderTool({ name: "render_floor_plan", render: ... })` custom renderer.
- Port existing renderers:
  - `ProductResultsToolRenderer`
  - `ImageToolOutputRenderer`
  - `DefaultToolCallRenderer` becomes the fallback renderer.

**Backend**

- Stabilize tool outputs:
  - `run_search_graph` should return displayable product fields (at minimum: `product_id`, `product_name`, `price_eur`, dims).
  - Consider evolving `ShortRetrievalResult` to include `product_name` explicitly to avoid UI guessing from `description_text`.

**Acceptance**

- Tool calls render as product cards / image panels, not raw JSON.

### Milestone 3: Image Uploads (Input) Using Shared State

**Frontend**

- Keep the existing `AttachmentComposer` UX.
- Add Next-side proxy endpoints for same-origin uploads:
  - `POST /api/attachments` -> forwards to Python `POST /attachments`
  - `GET /attachments/:id` -> forwards to Python `GET /attachments/:id`
- After successful upload(s):
  - `agent.setState({ attachments: AttachmentRef[] })`
  - Ensure attachments are cleared or preserved based on UX choice:
    - Recommended: preserve until user removes them.

**Backend**

- Define `AgentState` (Pydantic model) that includes:
  - `attachments: list[AttachmentRef] = []`
  - optional: `thread_id`, `room_profile`, etc. (keep minimal)
- Update AG-UI deps type to include `state`:
  - Create a deps dataclass that includes both our existing runtime deps and a `state` field.
  - Use `agent.to_ag_ui(deps=Deps(state=AgentState(), runtime=...))`.

**Acceptance**

- Images can be attached and are visible in UI.
- Agent tools can reference attached images (by attachment_id) without CORS / origin issues.

### Milestone 4: Image Outputs (Agent Shows Images)

**Backend**

- Standardize an image tool output contract:
  - `ImageToolOutput(caption: str, images: list[AttachmentRef])`
- Ensure tools return `AttachmentRef.uri` that resolves from the browser (via Next proxy route).
  - Prefer returning `/attachments/{id}` and having Next proxy it.
- Update `render_floor_plan` tool to optionally return an `ImageToolOutput` instead of only filesystem paths or binary blobs.
  - Recommended: always store to `AttachmentStore` and return `AttachmentRef`.

**Frontend**

- Tool renderer displays `ImageToolOutput` images using thumbnails + modal viewer.

**Acceptance**

- Agent can produce a floor plan image and UI renders it inline.

## Tool Rendering Contract (Repo Standard)

For each backend tool we expose to the agent, we define:

1. Stable tool name (string) and typed input/output models.
2. A frontend renderer registered with `useRenderTool({ name, render })`.
3. A fallback renderer via `useDefaultRenderTool`.
4. Tests:
   - UI unit test for renderer behavior (status transitions + empty/error cases)
   - Backend test for tool output shape stability

This contract is also codified in `AGENTS.md` so new tools don’t regress the UX.

## Open Questions / Risks

- Confirm CopilotKit v2 CSS path (`@copilotkit/react-ui/v2/styles.css`) matches the versions we install.
- Decide whether to keep `ui/src/app/api/agui-run/route.ts`:
  - Recommended: keep as debug-only or delete once CopilotKit UI covers all needs.
- Decide if we want per-thread persistent state in backend (requires storage) or keep state ephemeral per run.

