# AGENTS.md

Repository-local collaboration and implementation rules.

## Repository structure (current)

- `src/ikea_agent/`: active Python runtime (FastAPI + pydantic-ai + pydantic-graph).
- `tests/`: pytest test suite (typed tests preferred).
- `spec/`: specs (including `spec/ui/` for CopilotKit integration).
- `external_docs/`: repo-local notes on external libraries and protocols.
- `plans/`: planning docs that describe direction and sequencing.
- `docs/`: user/developer docs and runbooks.
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

## Tooling Standards

- Python environment and commands run through UV.
- **Pre-commit quality gate: `make tidy`** (runs format → lint-fix → typecheck → test in one command).
- Use `make format-all` for a quick format+lint pass without running the test suite.

## Typing and Test Expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses/protocols.
- Add tests for new behavior; test extensively.
- Maintain 98%+ coverage on all code in `src/` (checked by `uv run pytest --cov`).
- Keep test files small, prefer parameterized tests. Make sure tests are fully type annotated.
- Prefer files under ~200 lines; split modules at ~300 before they become hard to scan.

## Chat Runtime Standards

- Treat FastAPI + pydantic-ai + pydantic-graph as the default web/runtime stack.
- Prefer chat-first UX and API surfaces over form-heavy page flows.
- Keep graph state minimal; pass intermediate payloads through typed nodes when possible.
- Prefer tools that return typed domain objects (for example `list[RetrievalResult]`) over preformatted prose.
- Keep agent prompts concrete, scenario-driven, and explicit about output structure.
- Prefer current lightweight generation models as defaults when they satisfy quality/cost needs; keep model choice configurable.
- Use module-level loggers (`getLogger(__name__)`) and log concise operational facts (query + result counts).
- Avoid hidden side effects in service constructors (for example auto-running schema SQL). Bootstrap runtime/schema explicitly at app startup.
- Keep route handlers thin: validate request payloads, call graph/services, return typed responses.

## Implementing Tools

- Implement new runtime tools under `src/ikea_agent/tools/`.
- Register tool functions directly in `src/ikea_agent/chat/agent.py` on the active pydantic-ai agent.
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
   - Registered in `src/ikea_agent/chat/agent.py` with a stable name.
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

## Adding Agents (High-Level Recipe)

In this repo we generally have a single chat runtime agent. "Adding an agent" usually means adding a
new agent capability via one or more **tools** (and sometimes a small supporting service/repo layer).
The goal is a tool contract that the model can call correctly on the first attempt, and that is easy
to test and evolve.

### 1. Choose The Smallest Surface Area

- Prefer a **single tool** with a single request model if the capability is self-contained.
- Prefer **multiple tools** only when they map to distinct user intents (e.g. `search_products`,
  `render_floor_plan`, `price_bundle`), not because the implementation has multiple internal steps.
- Put complexity behind typed nodes/services; keep the agent-facing request minimal.

### 2. Use The Standard Directory Structure

- Create a package: `src/ikea_agent/tools/<tool_name>/`
- Typical layout (keep files short):
  - `models.py`: Pydantic request/response models and conversion helpers
  - `tool.py`: the agent-facing tool function(s) (thin wrappers)
  - `renderer.py` / `service.py`: integration code that can be tested independently
  - `__init__.py`: re-exports (keep public surface obvious)
- Tests:
  - `tests/tools/test_<tool_name>_models.py`
  - `tests/tools/test_<tool_name>_renderer.py` (or `..._service.py`)
  - `tests/tools/test_<tool_name>_tool.py`
  - Optional fixtures under `tests/fixtures/<tool_name>/`

### 3. Design Agent-Friendly Request Models

Keep the model from guessing. Make fields explicit, descriptive, and hard to misuse.

- Prefer a **single request model** (e.g. `FloorPlanRequest`) instead of raw dicts/YAML.
- Put critical semantics in the name:
  - include units in field names (`width_cm`, `length_m`)
  - include coordinate systems (`anchor_point_cm`, `orientation_angle_deg`)
  - include stable identifiers (`name`, `element_id`) for retries and UI rendering
- Use defaults aggressively for low-leverage knobs (dpi, colors, layout steps). If the model does not
  need a decision, do not ask it to provide the field.
- When the request contains heterogeneous elements, use a **discriminated union**:
  - `Annotated[Wall | Door | Window, Field(discriminator="type")]`
  - Keep a small set of `Literal[...]` tags; avoid free-form `"kind"` strings.
- Validators:
  - Only add high-leverage invariants that prevent downstream failure (e.g. non-negative sizes,
    unique names, door width <= doorway width).
  - Avoid doing heavy geometry or layout validation in the request unless it is required and stable.
- Conversion:
  - Put conversion helpers on the model (`to_renovation_settings(...)`, `to_api_payload(...)`).
  - Ensure conversion is **idempotent** (no mutation of the request).
  - Return typed structures where possible; when returning dicts, prefer narrow typed wrappers
    (`TypedDict`) in integration layers.

### 4. Implement Thin Tools With Stable Outputs

- Tool functions should:
  - validate the request (Pydantic does most of this)
  - call a renderer/service
  - return a typed success model, and raise a clear error on failure
- If returning binary artifacts (images), keep a stable file name and location under `artifacts/`
  (or `tmp_path` in tests) and optionally return `ToolReturn` with `BinaryContent`.
- Use `ToolReturn.metadata` for idempotent UI rendering keys (counts, element names, output paths).
- Keep route handlers thin (request -> service -> response), matching "Chat Runtime Standards".

### 5. Register The Tool On The Active Agent

- Register the tool(s) directly in `src/ikea_agent/chat/agent.py`.
- Prefer typed function signatures and typed request/response models.
- Keep the tool docstring concrete: what it does, what the request must contain, what it returns.

### 6. Testing: Example-Based + Property-Based

Target: fast validation coverage plus a small integration smoke that proves the renderer/tool works.

- Model tests (fast, many cases):
  - valid payload acceptance
  - invalid payload rejection (precise error messages)
  - schema friendliness (`model_json_schema` includes descriptions and examples)
  - conversion uses correct units and is idempotent
- Renderer/service tests (integration smoke):
  - write artifacts to `tmp_path` with stable naming (`floor_plan.png`, etc.)
  - assert artifact exists and size > 0
  - assert returned counts/metadata match the request
- Hypothesis (property tests):
  - generate *plausibly viable* requests (not random noise)
  - keep renderer-heavy runs low `max_examples` and `deadline=None`
  - run many examples for request/settings invariants
  - when asserting `ToolReturn.content`, narrow the type in tests (e.g. `BinaryContent`) because
    `content` is a broad union in pydantic-ai

### 7. Finish Strong: Quality Gate + Docs

- Before committing: `make tidy` (format → lint-fix → typecheck → test).
- Add a short plan in `plans/` for substantial work.
- Update `docs/` and `external_docs/` when you introduce new dependencies or protocols.

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

## Git Identity

- This repo must use the public identity:
  - `user.name = Talo Lard`
  - `user.email = talolard@users.noreply.github.com`
- Verify before pushing:
  - `git config --local --get user.name`
  - `git config --local --get user.email`
  - `./scripts/check_git_identity.sh`

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking except the exceptions described below
Plans and specs give our direction, define the work in beads.

Each task in beads that you add should

- Have a title of what the task is "Save vectors in parquet format" not "Use parquet"
- Have a context section "Currently we recompute vectors in dev, easier to store in parquet so duckdb can just load them quickly"
- Have a definition of done section "All embeddings are stored in parquet, paritioned, test checks we can load them and create an index + queries still work"
- Reference plan spec and additional md files , as well as the docs and external docs.

### When not to use bd / beads

- When the user asks you to plan or research, don't put planning and research in beads just do it.
- When the user asks for small exploratory work or a check ("which file is this function in?", "what does this error mean?") do the work and report back without creating beads. If you find something that needs follow-up work, create a bead for the follow-up but not for the initial exploration.

### Closing a task

- Before closing: run `make tidy`, ensure coverage, write a descriptive commit message, and commit. Then close the task.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists aside from what the user tells you to.
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
