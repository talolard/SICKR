# AGENTS.md

Repository-local collaboration and implementation rules.

## Repository structure (current)

- `src/ikea_agent/`: active Python runtime (FastAPI + pydantic-ai).
- `tests/`: pytest test suite (typed tests preferred).
- `spec/`: specs (including `spec/ui/` for CopilotKit integration).
- `external_docs/`: repo-local notes on external libraries and protocols.
- `plans/`: planning docs that describe direction and sequencing.
- `docs/`: user/developer docs and runbooks.
- `comments/`: local UI feedback bundles for debug triage (`comment.md` + artifacts per report).
- `legacy/`: reference-only; do not import from active runtime.
- `ui/`: Next.js (App Router) + React + TypeScript CopilotKit UI workspace.

# External Documentation

When using libraries search for documentation in

1. `./external_docs/` for any docs we've already collected on the library
2. search the context7 mcp for the library docs, store relevant parts in external_docs

## Workflow

- Create/update design plans in `plans/` before substantial changes (plans describe *direction*; use beads for *work tracking*).
- At task completion, add or update relevant docs in `docs/`.
- Keep changes scoped and incremental; avoid broad refactors during setup.
- Commit at the end of each implementation subtask.
- Commit messages must be high-level and human-readable, focused on intent.
- Commit bodies should explain problem -> approach -> outcome, not just file lists.

## Project Stage

- This repository is pre-production.
- For exploratory prompt/eval work, a small hand-authored dataset and an uncalibrated LLM judge are acceptable unless explicitly asked to harden them.
- Do not demand production-grade eval governance, production-traffic-derived datasets, or human-calibration loops by default for early exploratory work.

## Codex Multi-Agent Role System

- Project-local Codex role definitions live in `.codex/config.toml`.
- Each role has:
  - a config file under `.codex/agents/<role>/config.<role>.toml`
  - a role prompt under `.codex/agents/<role>/prompt.<role>.md`
- Shared prompt guidance lives under `.codex/prompt_support/`.
- `AGENTS.md` keeps repo-wide policy only; role-specific behavior belongs in the role prompts.
- The top-level session should behave like the coordinator-oriented `default` role.


## Agent Fast Paths

- Mutating implementation work must start in a dedicated worktree:
  - `make agent-start SLOT=<0-99> ISSUE=<bead-id>`
  - `make agent-start SLOT=<0-99> QUERY="<text>"`
- Merge runs are explicit and should not use normal `bd ready` pickup:
  - `make merge-list`
  - Follow `docs/merge_runbook.md` for one-by-one merge handling.

## Worktree + Merge Queue Policy

- Keep one worktree per epic/major task branch and avoid mutating work in the main checkout, unless the user explicitly overrides that for a specific task.
- Remove merged worktrees immediately after post-merge verification.
- Merge queue parent is `tal_maria_ikea-0uk` (`awaiting-merge`).
- Merge queue items must be `issue_type=merge-request`, `status=blocked`, and assigned to `merger-agent`.
- Because merge queue items are blocked, they should never appear in default `bd ready` pickup.
- Use `make merge-normalize` to enforce queue structure after migrations/drift.
- Merge ownership stays split across roles; see the role prompts for detailed responsibilities.

## Tooling Standards

- Python environment and commands run through UV.
- **Pre-commit quality gate: `make tidy`** (runs format → lint-fix → typecheck → test in one command).
- Use `make format-all` for a quick format+lint pass without running the test suite.

### Local Probe Isolation

- When running startup or performance probes alongside a live local session, use alternate ports and isolated local state.
- For extra backend instances, override `DUCKDB_PATH` and `MILVUS_LITE_URI` to temp files so the probe does not contend with the main dev server's `data/ikea.duckdb` lock.
- If the probe writes artifacts or feedback bundles, also override `ARTIFACT_ROOT_DIR`, `FEEDBACK_ROOT_DIR`, and `TRACE_ROOT_DIR` to temp directories.
- Do not run a second `next dev` from the same checkout; Next uses `ui/.next/dev/lock`. Use a separate worktree or checkout for parallel UI dev servers.

## Behavioral Readiness Gate

- For behavioral/runtime changes (agent logic, prompts, tools, routing, or UI behavior), run `make ui-test-e2e-real-ui-smoke` and ensure it passes before telling the user work is ready.
- This gate is not required for documentation-only changes.

## Typing and Test Expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses/protocols.
- Add tests for new behavior; test extensively.
- Maintain 98%+ coverage on all code in `src/` (checked by `uv run pytest --cov`).
- Keep test files small, prefer parameterized tests. Make sure tests are fully type annotated.
- Prefer files under ~200 lines; split modules at ~300 before they become hard to scan.

## Chat Runtime Standards

- Treat FastAPI + pydantic-ai as the default web/runtime stack.
- Prefer chat-first UX and API surfaces over form-heavy page flows.
- Keep agent state minimal and typed per agent.
- Prefer tools that return typed domain objects (for example `list[RetrievalResult]`) over preformatted prose.
- Keep agent prompts concrete, scenario-driven, and explicit about output structure.
- Prefer current lightweight generation models as defaults when they satisfy quality/cost needs; keep model choice configurable.
- Use module-level loggers (`getLogger(__name__)`) and log concise operational facts (query + result counts).
- Avoid hidden side effects in service constructors (for example auto-running schema SQL). Bootstrap runtime/schema explicitly at app startup.
- Keep route handlers thin: validate request payloads, call agents/services, return typed responses.

## Implementing Tools

- Implement new runtime tools under `src/ikea_agent/tools/`.
- Register tools in per-agent toolset modules under `src/ikea_agent/chat/agents/<agent_name>/toolset.py`.
- Register agent builders and metadata in `src/ikea_agent/chat/agents/index.py`.
- Prefer Pydantic models for tool inputs/outputs

## Tool Rendering (CopilotKit)

When a tool is intended to be user-visible (progress and/or results), it must have a defined frontend rendering contract.

### Backend Requirements

- Tool names are stable API:
  - Changing a tool name is a breaking UI change and requires coordinated backend+UI updates.
- Tool inputs and outputs must be JSON-serializable and versionable:
  - Prefer Pydantic models (or frozen dataclasses) with explicit fields.
  - Avoid “stringly typed” JSON blobs.
- Image output tools must return `ImageToolOutput` with `AttachmentRef` URIs that the browser can resolve.

### Frontend Requirements

- Every user-visible tool has a renderer registered via CopilotKit v2 hooks:
  - `useRenderTool({ name: "<tool_name>", render })` for named tools.
  - `useDefaultRenderTool({ render })` as a fallback for any unrecognized tools.
- Renderer output must be idempotent with respect to retries/replays:
  - Key progressive UI on `tool_call_id` and tolerate rerenders without duplication.
- Tool renderers live under `ui/src/components/tooling/` and should be small, typed components.

### “Tool to Renderer” Definition of Done

For a new tool `<tool_name>`:

1. Backend:
   - Implemented under `src/ikea_agent/tools/...` with typed input/output.
   - Registered in an agent-local toolset under `src/ikea_agent/chat/agents/<agent_name>/toolset.py` with a stable name.
2. UI:
   - Renderer exists at `ui/src/components/tooling/<ToolName>ToolRenderer.tsx`.
   - Registered in a single renderer registry (one place) via `useRenderTool`.
   - Has a unit test (`*.test.tsx`) that covers status transitions and empty/error cases.
3. Fallback:
   - A default renderer exists so unexpected tools are still visible in development.

### Shared State (Attachments and Progress)

If the tool depends on UI context (for example attachments), prefer passing it through the agent shared state and keep it typed:

- UI writes state via `agent.setState(...)`
- Backend tools read it from `ctx.deps.state` (deps must implement the AG-UI `StateHandler` protocol by having a `state` field)

## UI + AG-UI integration (CopilotKit + PydanticAI)

These are the protocol-level practices we follow for the CopilotKit UI integration (see `external_docs/pydantic_ai_ag_ui.md` and `spec/ui/pydanticai_copilotkit_integration.md`):

- Expose the agent using `Agent.to_ag_ui(deps=...)` and mount the returned ASGI app into the FastAPI runtime.
- Expect streaming over SSE (and possibly WebSocket routes depending on configuration); the stream can include:
  - assistant text deltas
  - tool call events (name/args/tool_call_id/results/errors)
  - optional “thinking” deltas (enabled at provider/model settings)
- Treat `tool_call_id` as a stable key in UI rendering; progressive tool rendering must be idempotent across retries/replays.
- Keep “thinking” behind a disclosure toggle by default; surface only a high-level “Thinking…” indicator unless explicitly expanded.
- Prefer explicit UI updates from tools via `ToolReturn` metadata (custom events or state snapshots) for progress updates and UI-only artifacts/state.
- For long-running work, prefer deferred tools and plan for multi-round-trip runs:
  - initial run yields deferred tool requests
  - follow-up run provides `DeferredToolResults` keyed by `tool_call_id`

## SQL and Data Rules

- Active runtime data access should use short, inline SQL in typed repository methods.
- Keep query text close to row-mapping code for readability and testability.
- Bootstrap runtime schema explicitly at startup; avoid hidden constructor side effects.
- Update `docs/data/` whenever active schema or column semantics change.
- Treat IKEA source data as static unless explicitly refreshing the dataset.
- For analysis, inspect aggregates and small result sets first.

## Legacy Policy

- `legacy/` is reference-only. Do not import from it or route implementation decisions through it.

## Logging

- Use shared logger configuration from `src/ikea_agent/logging_config.py`.
- Include query/request IDs in pipeline logs where available.
- Default to native Logfire instrumentation (`instrument_pydantic_ai`, `instrument_fastapi`).
- Do not add custom event taxonomies unless a concrete query/debug gap is proven.
- In discovery mode, missing observability fields should warn and create follow-up work;
  hard CI failure for observability schema is deferred.
- For span-level debugging and telemetry-to-code correlation, use the local skill:
  `~/.codex/skills/logfire-span-triage` (script + checklist for repeatable trace/span triage).

## Git Identity

- This repo must use the public identity:
  - `user.name = Tal Perry`
  - `user.email = talperry@users.noreply.github.com`
- Verify before pushing:
  - `git config --local --get user.name`
  - `git config --local --get user.email`
  - `./scripts/check_git_identity.sh`

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

Use **bd** as the only issue tracker.

- Default workflow:
  - `bd ready --json` for normal implementation pickup
  - `bd update <id> --status in_progress --json` to claim
  - `bd close <id> --reason "Done" --json` when complete
- Do not create beads for pure planning/research or tiny exploratory checks.
- Every created issue should include: context, definition of done, and references.
- Before closing an implementation issue: run `make tidy`, commit, then close.

### Merge Queue Exception

- Merge queue work is not part of normal `bd ready` pickup.
- Use `make merge-list` for explicit merge runs.
- Merge queue items under `tal_maria_ikea-0uk` must remain:
  - `type=merge-request` when supported by current `bd` version
  - otherwise keep `label=merge-request` as compatibility marker
  - `status=blocked`
  - `assignee=merger-agent`

<!-- END BEADS INTEGRATION -->
