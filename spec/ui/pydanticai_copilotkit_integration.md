# Spec: PydanticAI + CopilotKit Integration

## Goal

Provide a production-ready path to replace or augment the built-in pydantic-ai web UI with CopilotKit while preserving current `ikea_agent` graph/tool behavior.

## Flows

### Flow: Collect measurements and validate layout

#### Exact measurements (text)

User: “Help me design my bedroom.”

Assistant: Asks for any of:
- measurements (exact preferred, approximate OK)
- photos
- constraints (budget, must-keep items, style preferences)

User: Provides measurements as free text (walls, openings, ceiling height).

Assistant:
- parses the measurements into a structured room model
- generates a simple floor plan image to confirm shared understanding
- asks the user to confirm/correct the plan

User: Corrects mistakes (e.g. door/window position), optionally adds missing measurements.

Assistant: Iterates until the user confirms the layout is “good enough”, then continues with planning and product placement.

#### Not needed (skip measurement)

User: “I’m looking for plants I can put in a dark hallway.”

Assistant:
- proceeds directly to recommendations
- optionally asks a minimal follow-up (e.g. “floor space vs. wall-mounted?”)
- offers an upgrade path (“If you share measurements/photos, I can be more precise.”)

#### From photos (approximate measurements)

User: Uploads photos and asks for a recommendation that depends on fit/style.

Assistant:
- acknowledges the images and starts analysis
- uses image analysis tools (when available) to infer rough layout and style cues
- produces a *draft* floor plan + a list of identified items (with uncertainty)
- asks the user to confirm/correct the draft before optimizing recommendations

User: Confirms or corrects (e.g. “that’s a bookshelf, not a wardrobe”; “the sofa is 240cm wide”).

Assistant: Updates the draft and proceeds once it is accurate enough to avoid obviously-wrong suggestions.

### Flow: Critique and guidance from photos

User: Uploads photos and asks “What can we do better?”

Assistant:
- analyzes for functional issues and aesthetics (clutter, lighting, storage, circulation)
- identifies signals about the user/room needs (age, activities, preferences)
- gives actionable improvements (quick wins + larger changes)
- asks targeted follow-ups (budget, must-keep items, safety constraints)

Optional: If placement/fit matters, the assistant transitions into the measurement flow (text measurements or “approx from photos”) and clearly labels any uncertainty.

## UI Requirements (Derived)

### Core UI components

- Chat shell based on `CopilotChat` (or `CopilotSidebar`) with streaming support.
- Message timeline that supports:
  - markdown/text assistant messages
  - inline images (user-uploaded and agent-generated)
  - a per-turn “activity” area for tool calls (collapsed by default once complete)
- Composer with attachments:
  - multi-image selection (drag/drop + file picker)
  - thumbnail strip with remove/reorder (optional reorder; remove is required)
  - upload progress per file and overall
  - clear “uploaded” vs “still uploading” state
- Tool call renderers:
  - default renderer for unknown tools (name + args + status + raw JSON result)
  - custom renderers for known tools (e.g. product search results as cards)
- Notifications:
  - transient toasts for non-blocking events
  - inline, actionable errors inside the chat stream for anything that blocks completion
- Image viewer:
  - click-to-zoom modal
  - download/open-in-new-tab affordance

### Cross-cutting interaction rules

- Sending messages:
  - If there are pending uploads, sending is blocked and the UI explains why (“Finish uploading or remove attachments to send.”).
  - On send, the UI echoes the user message immediately (optimistic), and shows a run-in-progress indicator.
- Streaming and partial updates:
  - Stream assistant text as it arrives.
  - Stream tool call start/args/result events and render them progressively.
  - If “thinking” is available, show only a high-level indicator by default (“Thinking…”); full thoughts are behind a disclosure toggle.
- Tool call UX:
  - Each tool call has: `name`, `status` (`queued` → `executing` → `complete` or `failed`), start/end timestamps, and a stable ID.
  - Multiple tool calls are grouped under the assistant turn that triggered them.
  - Failures show: what failed, what the user can do (retry / change input), and (in dev) a debug panel.
- Recovery:
  - If a run fails due to network/server errors, the UI offers a one-click retry that re-sends the same message payload (including attachment refs).
  - If only a tool call fails (others succeed), the UI offers a targeted retry (if supported) or suggests a minimal re-ask (“Try again, but with …”).

### Long-running work and progress

- “Long-running” definition (initial): any single tool call expected to take > 10s, or any full run expected to take > 20s.
- The UI must keep the user informed without flooding:
  - a single top-level “Working…” indicator per run
  - per-tool progress UI (spinner + short label; progress bar if percent known)
  - a compact counter (“3 tools running”) when multiple tools execute
- The user can cancel a run:
  - cancels client streaming immediately
  - best-effort cancellation on the backend (if supported), otherwise UI clarifies “canceled locally”

### Attachment UX (images)

- Happy path:
  - show upload progress per file
  - on completion, show a “ready” indicator per thumbnail
  - after the agent responds, render images inline in the conversation (with captions if available)
- Required failure cases:
  - upload error (network, file too large, unsupported type): show inline error per file + “retry upload” + “remove”
  - message send failure after upload success: keep attachments and allow “retry send”
  - attachment reference missing/expired server-side: show “image unavailable” placeholder and suggest re-upload

## Flow-by-Flow UI Sequences

Each flow below lists the UI sequence, happy path, and likely failure cases. Cross-cutting behaviors (streaming, tool call rendering, notifications, cancellation) apply to all flows.

### Flow: Exact measurements (text) → validate floor plan

**Sequence**
1. User sends a design goal.
2. Assistant asks for measurements/photos/constraints.
3. User sends free-text measurements.
4. Agent triggers tools to parse measurements and generate a floor plan image.
5. UI renders the image inline and prompts for confirmation (“Does this look right?”).
6. User corrects; agent iterates until confirmed; then continues.

**Happy path**
- Tool calls complete quickly; floor plan image renders; user confirms after 0–2 iterations.

**Likely failure cases + user messaging**
- Measurements ambiguous/incomplete: assistant asks focused clarifying questions; UI highlights them (e.g. “missing window wall location”).
- Floor plan generation fails: UI shows tool failure and assistant provides a fallback (“I can proceed without a floor plan, or you can rephrase measurements.”).
- User corrects repeatedly: assistant switches to a more structured measurement capture (e.g. a short checklist) to reduce churn.

### Flow: Quick recommendations (skip measurement)

**Sequence**
1. User sends a request that does not require fit precision.
2. Agent calls retrieval tools and returns a ranked list.
3. UI renders results as product cards and keeps the chat narrative short.

**Happy path**
- `run_search_graph` returns results; UI renders cards with minimal friction.

**Likely failure cases + user messaging**
- No results: assistant proposes alternatives (broader query, adjacent category) and suggests a follow-up question.
- Retrieval backend error: UI shows a retry and assistant suggests a text-only workaround (“Tell me your budget/style; I can still suggest categories.”).

### Flow: Photos → draft layout + refinement → recommendations

**Sequence**
1. User uploads 1+ photos and types a request.
2. UI uploads images, then sends the message with attachment refs.
3. Agent calls image analysis tools and/or retrieval tools using extracted context.
4. UI renders:
   - tool call progress (analysis running)
   - draft floor plan image (if produced)
   - identified items (as a structured list)
5. Assistant asks for corrections; user confirms/corrects; agent updates plan and recommendations.

**Happy path**
- Upload succeeds; image analysis produces a reasonable draft; the user confirms with small corrections.

**Likely failure cases + user messaging**
- Upload fails or stalls: UI shows per-file retry; sending is blocked until resolved.
- Image analysis unavailable (model/tool missing): assistant asks for text measurements as fallback and continues.
- Low-confidence/contradictory detections: assistant clearly labels uncertainty and asks 1–3 targeted questions (“Is the rug ~200×300cm?”).
- Privacy concern: UI provides an explicit note (“Images are used to answer your request”) and supports removal of attachments before sending.

### Flow: Critique and guidance from photos

**Sequence**
1. User uploads photos and asks for critique.
2. Agent runs analysis tools and returns:
   - a short summary (“what I see”)
   - prioritized recommendations (quick wins → bigger changes)
   - follow-up questions
3. UI renders tool call results (optional) and the final critique as a structured response (sections, bullets).

**Happy path**
- Analysis completes; user gets actionable guidance and next steps.

**Likely failure cases + user messaging**
- User wants product-specific placements: assistant explicitly asks for measurements and transitions to the measurement flow.
- Conflicting constraints (budget vs wishlist): assistant surfaces the tradeoff and asks which to prioritize.

### Flow → CopilotKit / PydanticAI capability mapping

| Flow | CopilotKit (out of the box) | UI we build | PydanticAI (AG-UI) | Backend we build |
| --- | --- | --- | --- | --- |
| Exact measurements → floor plan validation | Streaming chat UI, tool-call UI hooks | Floor plan image renderer + confirm/correct affordances | Tool calls + streaming events (text/tool/thinking) | Measurement parsing + floor plan generation tools; image artifact storage |
| Quick recommendations | Streaming chat UI | Product cards + “no results” UX | Tool calls + typed tool results | Retrieval tool(s) + stable `ShortRetrievalResult` contract |
| Photos → draft layout → refine | Streaming chat UI, tool-call UI hooks | Attachment composer + upload UX; image viewer; “uncertainty” UI patterns | Tool calls + custom events/state snapshots (optional) | Attachment upload/store; image analysis tools; draft plan tools; error/fallback paths |
| Critique and guidance | Streaming chat UI | Structured critique renderer (sections + bullets) | Tool calls + streaming | Image analysis/critique tools; guardrails for uncertainty |

## CopilotKit ↔ PydanticAI (AG-UI) Mapping

### Transport and runtime wiring

- CopilotKit runtime runs in Next.js at `POST /api/copilotkit` via `CopilotRuntime` + `copilotRuntimeNextJSAppRouterEndpoint`.
- CopilotKit connects to Python via an AG-UI `HttpAgent` (`@ag-ui/client`) pointing at the FastAPI-hosted AG-UI endpoint.
- Python exposes the agent as an ASGI app using `agent.to_ag_ui(deps=...)` and mounts it in the FastAPI server.

### Streaming: assistant text, thinking, and tool calls

- PydanticAI streams events (SSE) that include:
  - assistant text deltas
  - thinking deltas (when enabled)
  - tool call start/args/result events
- CopilotKit forwards these events to the UI:
  - assistant message text is rendered as it streams
  - tool calls appear as “executing” and then “complete/failed”
  - thinking is mapped to a UI-only channel; default is “collapsed”

### Tool-call rendering (generative UI)

- CopilotKit supports per-tool UI via `useRenderToolCall({ name, parameters, render })`.
- This maps naturally to PydanticAI tools:
  - tool name stability becomes a UI contract
  - tool result types should be JSON-serializable and versioned if they evolve

### Progress, multi-step runs, and long-running tools

- PydanticAI supports “deferred tools” for long-running work; the UI must tolerate multiple round-trips before a final answer.
- For progress updates, prefer emitting explicit AG-UI events (e.g. custom events or state snapshots) rather than relying on verbose model narration.
- CopilotKit must surface these events to the frontend so the UI can update progress indicators. If a given event type is not supported out of the box, we treat it as an explicit integration task (frontend event handling + a minimal schema).

### Images: upload, retrieval, and display

- CopilotKit provides the chat shell and tool-call UI; image upload and storage are application concerns:
  - frontend uploads images to an app endpoint and receives `AttachmentRef` objects
  - attachment refs are included in the agent run input (AG-UI state and/or tool args)
  - tools that produce images return `AttachmentRef` (or emit an explicit image event) so the UI can render inline images

## Architecture

### Backend (Python)

1. Keep `ikea_agent` FastAPI runtime as the source of truth for agent logic.
2. Expose agent via AG-UI compatible endpoint (`agent.to_ag_ui(...)`).
3. Keep retrieval tool contract typed (`list[ShortRetrievalResult]`).
4. Add image-aware tools:
   - `analyze_uploaded_image(image_ref: str, prompt: str) -> ImageAnalysisResult`
   - `search_with_image_context(image_ref: str, user_query: str) -> list[ShortRetrievalResult]`

### UI (CopilotKit + Next.js)

1. Add CopilotKit runtime route (`/api/copilotkit`) with `CopilotRuntime` and an AG-UI `HttpAgent` pointed at the Python server.
2. Use `CopilotChat` / chat components to render:
   - assistant/user messages
   - tool call status and outputs
   - structured product lists/cards
3. Add image upload widget in composer:
   - uploads to app storage endpoint
   - inserts attachment reference into agent message context
4. Add image message renderer:
   - render returned image URLs or data refs inline in conversation timeline.

## Contracts

### Transport protocol

- Baseline transport is AG-UI (PydanticAI ↔ CopilotKit via `HttpAgent`).
- Any additional UI features (attachments, progress, image outputs) must be expressed in one of:
  - tool args and tool return values
  - AG-UI custom events / state snapshots (preferred for progress + UI-only data)

### Attachment references (application-level)

- `attachments: list[AttachmentRef]` on user turns

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

## Build Order (Key Features)

### Milestone -1: UI dev environment + testing infrastructure (TypeScript)

**Goal**
- A local, TypeScript-first UI environment that can run against (a) a mock AG-UI agent (fast, deterministic) and (b) the real Python AG-UI endpoint (integration mode).
- A test stack that can validate streaming, tool calls, attachments, and failures without depending on the Python backend for most tests.

**CopilotKit components (TypeScript)**
- Runtime wiring:
  - `CopilotRuntime`, `copilotRuntimeNextJSAppRouterEndpoint`, `ExperimentalEmptyAdapter` from `@copilotkit/runtime`
  - `HttpAgent` from `@ag-ui/client` (connects runtime → Python AG-UI)
- UI:
  - `CopilotKit` provider (from `@copilotkit/react-core`)
  - `CopilotChat` (from `@copilotkit/react-ui`)
  - `useRenderToolCall` (from `@copilotkit/react-core`) for tool call renderers

**Custom components we build (TypeScript, incl. containers)**
- App layout containers:
  - `CopilotKitProviderContainer` (typed env/config, installs CopilotKit provider)
  - `ChatPageContainer` (page shell + layout)
  - `CopilotChatContainer` (wraps `CopilotChat`, central place to configure message/tool renderers)
  - `ToolRenderersContainer` (registers `useRenderToolCall(...)` handlers)
- Foundational UI primitives:
  - `InlineErrorBanner` (blocking errors in the timeline)
  - `ToastCenter` (non-blocking notifications)
  - `DebugPanel` (dev-only, shows last events payloads)

**Best practices (TypeScript)**
- Framework and tooling:
  - Next.js App Router + React + TypeScript in a dedicated `ui/` workspace.
  - Package manager: `pnpm` managed via `corepack` (avoids “global pnpm version drift”).
  - Pin Node (recommend Node 20 LTS) via `.nvmrc` or equivalent.
- Type safety:
  - `tsconfig.json` with `strict: true`, plus `noUncheckedIndexedAccess: true` and `exactOptionalPropertyTypes: true`.
  - Validate tool outputs and any custom event payloads at renderer boundaries using runtime schemas (recommend `zod`).
- Streaming correctness:
  - Render tool calls idempotently keyed by `tool_call_id`.
  - Avoid duplicate UI on retries/reconnects (event replay should not double-render).
- Styling:
  - Import `@copilotkit/react-ui/styles.css` for baseline CopilotKit UI.
  - Use a lightweight app styling layer (recommend Tailwind) for our containers and custom tool renderers.

**Testing (TypeScript)**
- Unit/component:
  - Vitest + React Testing Library for containers and tool renderers.
  - MSW for HTTP mocking in unit tests.
- E2E:
  - Playwright for end-to-end UX (typing, streaming, tool call rendering).
  - A mock AG-UI “scripted SSE server” to deterministically simulate:
    - streamed assistant text
    - tool call executing → complete/failed
    - disconnect mid-stream

**Acceptance criteria**
- `pnpm dev:mock` runs the UI and streams a scripted response + tool call.
- `pnpm test` and `pnpm test:e2e` pass locally without the Python backend running.

### Milestone 0: End-to-end chat wiring

**CopilotKit components (TypeScript)**
- Runtime route: `CopilotRuntime`, `copilotRuntimeNextJSAppRouterEndpoint`, `ExperimentalEmptyAdapter`
- Agent transport: `HttpAgent`
- UI: `CopilotKit` provider + `CopilotChat`

**Custom components we build (TypeScript, incl. containers)**
- `CopilotRuntimeRoute` (Next.js route handler in TypeScript under `/api/copilotkit`)
- `CopilotKitProviderContainer` + `CopilotChatContainer` wired to the real backend URL

**Backend work (Python)**
- Mount `agent.to_ag_ui(deps=ChatGraphDeps(...))` into the FastAPI app so it is reachable by the UI runtime.

**Testing**
- Playwright smoke test (real backend mode): “send message → streamed assistant response appears”.
- Keep mock-based E2E tests as the default fast path; run real-backend E2E as a smaller smoke suite.

**Required behaviors / edge cases**
- If streaming disconnects mid-run: show an inline error and allow retry.
- Retry semantics are explicit: either idempotent retries (preferred, requires run ID) or “retry creates a new run” (documented).

### Milestone 1: Tool call visibility + product cards

**CopilotKit components (TypeScript)**
- `useRenderToolCall` to render tool calls with custom UI.
- Optional (if needed for inline tool-call blocks): `CopilotChatToolCallsView` from `@copilotkit/react-core/v2`.

**Custom components we build (TypeScript, incl. containers)**
- Container:
  - `ToolRenderersContainer` registers a renderer for `run_search_graph`
- UI:
  - `ToolCallDefaultRenderer` (name + args + status + raw JSON)
  - `ProductResultsToolRenderer` + `ProductCard` for `ShortRetrievalResult[]`

**Backend work (Python)**
- Keep `run_search_graph` output stable and JSON-friendly.

**Testing**
- Unit/component: tool renderer renders product cards from a mocked tool result; failure result renders actionable guidance.
- E2E (mock agent): “tool call executing → complete → product cards render”; multiple tool calls remain grouped and ordered.

**Required behaviors / edge cases**
- Tool failures render as `failed` with retry guidance (and dev debug details behind a toggle).
- Multiple tool calls in one run render deterministically (stable ordering, no duplication on rerender).

### Milestone 2: Image attachments (upload + pass-through)

**CopilotKit components (TypeScript)**
- CopilotKit provides the chat shell; attachment UX is application code.

**Custom components we build (TypeScript, incl. containers)**
- Container:
  - `AttachmentComposerContainer` (selected files, upload state machine, retries)
- UI:
  - `AttachmentThumbnailStrip` (remove required; reorder optional)
  - `UploadProgressBar` (per-file + overall)

**Backend work (Python)**
- Attachment storage endpoint that returns `AttachmentRef` with a stable `attachment_id`.
- Image-aware tools accept `attachment_id`/`uri` and fetch bytes server-side.

**Testing**
- Unit/component:
  - upload progress → completion state per file
  - failure shows inline retry/remove
  - “send” is blocked while uploads pending with an explanatory message
- E2E (mock agent):
  - attach image → upload completes → message send includes attachment refs

**Required behaviors / edge cases**
- Upload progress and upload completion are explicitly visible per file.
- Enforce size/type limits with friendly client + server errors.
- If message send fails after upload succeeds: keep attachments and allow “retry send” without re-upload (within TTL).

### Milestone 3: Image outputs (floor plans, annotated images)

**CopilotKit components (TypeScript)**
- `useRenderToolCall` for image-producing tools (render tool outputs as inline images).

**Custom components we build (TypeScript, incl. containers)**
- UI:
  - `ImageMessageRenderer` (inline image(s) + caption)
  - `ImageViewerModal` (zoom + download/open)
  - `BrokenImagePlaceholder`

**Backend work (Python)**
- Generate/store image artifacts and return `AttachmentRef` for each image.
- Add tools for floor plan generation and/or annotated image outputs.

**Testing**
- Unit/component: render `ImageToolOutput` and verify viewer modal interactions.
- E2E (mock agent): tool emits an image output; image renders and opens in viewer.

**Required behaviors / edge cases**
- Broken/missing image URLs render a placeholder with “try again” guidance.
- Large images don’t break layout (responsive sizing + lazy loading).

### Milestone 4: Long-running tasks + progress + cancellation

**CopilotKit components (TypeScript)**
- Same streaming pipeline; progress UI is driven by tool status and/or explicit AG-UI events forwarded by CopilotKit.

**Custom components we build (TypeScript, incl. containers)**
- Containers:
  - `RunStatusContainer` (one top-level “Working…” + “N tools running” counter)
  - `CancelableRunController` (cancel button + local cancellation semantics)
- UI:
  - `ToolProgressRow` (executing/percent/label)

**Backend work (Python)**
- Use deferred tools for long-running work where needed.
- Emit progress via explicit AG-UI events (custom events or state snapshots) rather than verbose assistant narration.

**Testing**
- Unit/component: progress event coalescing (no timeline spam), cancel transitions UI to “canceled”.
- E2E (mock agent): scripted long tool call with progress updates; cancel mid-run stops streaming and labels partial results.

**Required behaviors / edge cases**
- Progress updates are throttled/coalesced in UI.
- After cancel: UI stops streaming immediately and clarifies “canceled locally” vs “canceled server-side” (if supported).

### Milestone 5: Sessions and persistence

**CopilotKit components (TypeScript)**
- CopilotKit provides chat UI primitives; session persistence is application-level.

**Custom components we build (TypeScript, incl. containers)**
- Containers:
  - `ThreadContainer` (thread id in URL, load history, reconnect behavior)
  - Optional: `ThreadListContainer` (“resume chat” UX)

**Backend work (Python)**
- Persist message history and minimal state (attachments + run metadata).
- Inject per-session state via PydanticAI AG-UI state mechanism (`StateHandler`) where appropriate.

**Testing**
- Unit/component: thread routing and history rendering.
- E2E: refresh mid-run either resumes streaming or shows “run still in progress”; sessions do not leak attachments across threads/users.

**Required behaviors / edge cases**
- Refresh mid-run has explicit behavior (resume vs “still running” status).
- Persisted sessions never leak attachments between users/threads.

## Testing

1. UI unit/component tests (Vitest + React Testing Library): containers + tool renderers.
2. UI E2E tests (Playwright): streaming, tool calls, attachments, image viewing, cancellation, reconnect.
3. Backend integration tests (Python): tool call events stream correctly; attachments and image outputs are stable and typed.
4. Regression test: text-only retrieval flow unchanged.

## Operational Notes

- Keep model/provider choices configurable via Python env settings.
- Keep typed schemas for all tool payloads and attachment metadata.
- Keep CopilotKit UI as a client layer; business logic remains in `ikea_agent` backend.
