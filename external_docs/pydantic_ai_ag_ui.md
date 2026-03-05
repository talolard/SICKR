# PydanticAI AG-UI notes (for this repo)

This repo uses PydanticAI’s AG-UI integration as the backend protocol for CopilotKit.

## Exposing an AG-UI endpoint

- `Agent.to_ag_ui(deps=...)` returns an ASGI app that serves AG-UI over HTTP (streaming via SSE) and, depending on configuration, may also serve WebSocket routes.
- The returned ASGI app can be mounted into the existing FastAPI runtime (similar to how we currently mount `agent.to_web(...)`).

## What streams to the UI

The agent run emits a stream of events that can include:
- assistant text deltas (streamed output)
- tool call events (tool name, args, tool_call_id, results/errors)
- optional “thinking” deltas when enabled at the model/provider level

UI implications:
- treat tool call IDs as stable keys for progressive rendering
- keep “thinking” behind a disclosure toggle by default

## Sending UI events from tools

Tools can emit AG-UI events by returning a `ToolReturn` with event metadata (e.g. custom events, state snapshots). This is the preferred mechanism for:
- progress updates (rather than verbose assistant narration)
- UI-only artifacts/state (e.g. image generation status)

## Long-running work

PydanticAI supports “deferred tools” for background execution. The initial run yields a set of deferred tool requests, and a follow-up run provides `DeferredToolResults` keyed by `tool_call_id`.

UI implications:
- a single user action may require multiple request/response round trips
- tool calls may remain “executing” across round trips until results arrive

