# CopilotKit notes (for this repo)

This is a small, repo-local summary of the CopilotKit capabilities we rely on for the `PydanticAI + CopilotKit Integration` spec.

## Runtime (Next.js)

- CopilotKit runtime is typically hosted as a Next.js App Router route at `POST /api/copilotkit`.
- The runtime is created with `CopilotRuntime` and exported using `copilotRuntimeNextJSAppRouterEndpoint`.
- When integrating with an external agent over AG-UI, the runtime can use an `HttpAgent` from `@ag-ui/client` pointed at the Python server’s AG-UI endpoint.

Key symbols (TypeScript):
- `CopilotRuntime`, `copilotRuntimeNextJSAppRouterEndpoint`, `ExperimentalEmptyAdapter` from `@copilotkit/runtime`
- `HttpAgent` from `@ag-ui/client`

## UI (React)

- `CopilotChat` provides a ready-made chat UI with streaming support.
- Tool calls can be rendered with custom UI via `useRenderToolCall({ name, parameters, render })`.
- Message rendering can be customized by overriding message components (e.g. custom assistant messages, custom messages list).

Key symbols (React):
- `CopilotChat`, `CopilotSidebar`, `Markdown` from `@copilotkit/react-ui`
- `useRenderToolCall` from `@copilotkit/react-core`
- `CopilotChatToolCallsView` from `@copilotkit/react-core/v2` (for rendering tool calls inside assistant messages)

