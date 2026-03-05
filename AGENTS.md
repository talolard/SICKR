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
2. search the context7 mcp for the library docs, store relevent parts in external_docs

## Workflow

- Create/update task plans in `plans/` before substantial changes.
- At task completion, add or update relevant docs in `docs/`.
- Keep changes scoped and incremental; avoid broad refactors during setup.
- Commit at the end of each implementation subtask.
- Commit messages must be high-level and human-readable, focused on intent.
- Commit bodies should explain problem -> approach -> outcome, not just file lists.

## Tooling Standards

- Python environment and commands run through UV.
- Use `make format-all` as the go-to local quality command (no tests).
- Run `make tidy` before commit.
- Quality gate for changes:
  - `make format-all`
  - `make test`

## Typing and Test Expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses/protocols.
- Add tests for new behavior; Test extensively.
- Use codecov and maintain 98%+ coverage on all code in `src/`.
- Keep test files small, prefer paramaterized tests. Make sure tests are fully type annotated.
- Keep files short and split modules before they become hard to scan.

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
- For floor planner specifically, use `src/ikea_agent/tools/floorplanner/` as the canonical module location.
- Register tool functions directly in `src/ikea_agent/chat/agent.py` on the active pydantic-ai agent.
- Prefer Pydantic models for tool inputs/outputs and avoid compatibility shim layers in legacy package paths.

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

- `legacy/` is reference-only and excluded from active implementation guidance.
- Do not import `legacy/` modules into active runtime code.
- When updating docs, prefer linking active docs and avoid routing implementation decisions through legacy files.

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
- When the user asks for small exploratory work or a check "which file is this function in?" "what does this error mean?" "what are the current embedding strategies we have?" do the work and report back without creating beads for it. If you find something that needs follow up work, then create a bead for the follow up work but not for the initial exploration.
-

### Closing a task

- Befoore closing, lint, type check, test, ensure coverage. Write a descriptive commit message and commit. Once all those happened, close the task.
-
-

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
