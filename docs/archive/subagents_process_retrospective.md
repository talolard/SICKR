# Subagents Process Retrospective

## Scope and question
This retrospective covers the subagent implementation sequence from commit `a1b6a6d` (2026-03-09) through `0add157` (2026-03-10), with focus on:
- intent vs actual outcome,
- adherence to `.codex/skills/build-graph-agent/SKILL.md`, and
- process controls needed to prevent repeat regressions.

## Evidence timeline

### 2026-03-09 - `a1b6a6d` - Add beta GraphBuilder floor-plan intake subagent
Intent:
- Create `floor_plan_intake` graph subagent scaffold with registry and CLI integration.

Delivered:
- Added graph/nodes/prompt/tools/tests under `src/ikea_agent/chat/subagents/floor_plan_intake/`.
- Added shared subagent plumbing (`registry.py`, `cli.py`, `common.py`).

Observed gap:
- Initial routing logic was deterministic heuristics, later revised.

### 2026-03-09 - `f25ed56` - Make floor-plan intake routing model-driven
Intent:
- Move routing decisions to model-backed structured classification.

Delivered:
- Added `intake_decider` model tool and routed `route_turn` through it.

Observed gap:
- README/tool inventory drifted (new tool added but documentation not fully synchronized).
- New model-backed behavior lacked dedicated deterministic tool-level tests.

### 2026-03-10 - `9f63e5d` - Add subagent directory page and web chat mounts
Intent:
- Surface subagents in UI and provide web chat entrypoints.

Delivered:
- Added `ui/src/app/subagents/*` pages and API routes.
- Added backend `subagents/web.py` and app mounts in `chat_app/main.py`.

Observed regressions introduced:
- Embedded chat/proxy URL behavior was incorrect for internal web calls.
- Subagent pages could still hit main `/api/chat` path without explicit dispatch.
- FunctionModel web wrapper lacked streaming support for chat runtime.

### 2026-03-10 - `af7344c` - Use direct backend URLs for subagent chat embed
Intent:
- Bypass broken proxy-relative embed behavior.

Delivered:
- UI now consumes backend `chat_url` for iframe/open-link.

Residual gap:
- Dispatch ambiguity for `/api/chat` still remained until follow-up.

### 2026-03-10 - `a677b49` - Route Pydantic web API by subagent chat context
Intent:
- Dispatch API routes to correct subagent app.

Delivered:
- Referer-based subagent context routing in `chat_app/main.py`.
- Additional API tests.

Observed fragility:
- Referer-dependent logic was brittle when referer absent.

### 2026-03-10 - `706ee66` - Fix subagent web chat model routing mismatch
Intent:
- Make dispatch robust when referer is absent.

Delivered:
- Added model-id-based fallback mapping and unique subagent model names.

Outcome:
- Fixed routing mismatch introduced by prior dispatch approach.

### 2026-03-10 - `0add157` - Add streaming support to subagent FunctionModel
Intent:
- Restore stream-compatible FunctionModel behavior.

Delivered:
- Added stream function wiring to subagent FunctionModel adapter.

Outcome:
- Fixed runtime streaming failure in subagent web chat path.

## Failure taxonomy and root causes

### 1) Integration-first regressions (UI/web runtime)
Symptoms:
- Correctly scaffolded subagent internals, but web runtime and routing contracts broke across multiple iterations.

Root cause:
- Lack of end-to-end integration gate for mounted subagent web chat (`/subagents/<agent>/chat` -> correct backend + streamed `/api/chat`).

### 2) Specification boundary mismatch
Symptoms:
- `build-graph-agent` skill covered subagent scaffold patterns well, but did not constrain web embedding, dispatch routing, model-id invariants, or streaming adapter requirements.

Root cause:
- Skill scope ended at graph/subagent structure and tests, while rollout included cross-layer UI+backend routing contracts not represented as required checks.

### 3) Drift between implementation and artifact docs/tests
Symptoms:
- Tool inventory and prompt wiring expectations diverged from actual runtime behavior.
- Model-backed decision tool did not receive dedicated deterministic tests.

Root cause:
- No automatic checks tying README tool table and prompt contract to real exports/runtime wiring.

## Expected vs actual (against skill guidance)

### Met
- Beta graph APIs used (`GraphBuilder`, `step`, `decision`) for subagent graph construction.
- Required scaffold largely present (`graph.py`, `nodes.py`, `prompt.md`, `tools/`, tests, registry/CLI).

### Partially met
- Prompt loading exists, but prompt-to-model wiring is not consistently enforced by tests.
- README exists with flow docs, but inventory drift occurred after tool evolution.

### Missed for practical rollout
- No skill-level requirement for web mounting + `/api/chat` dispatch correctness.
- No required streamed web chat integration test for FunctionModel adapters.
- No startup invariant to enforce unique model ids and deterministic subagent routing.

## Prevention controls
1. Add subagent web integration contract tests (route dispatch + streaming path) in CI.
2. Add startup invariant checks for unique subagent model ids and dispatch map integrity.
3. Add a doc/test lint that keeps README tool inventory and prompt wiring synchronized with code.
4. Extend `build-graph-agent` skill checklist with explicit web integration requirements when a subagent is user-facing in UI.

## Beads follow-up tracking
Follow-up prevention tasks were created under epic `tal_maria_ikea-ndq`:
- `tal_maria_ikea-3t1`: Add subagent web integration contract tests for dispatch and streaming.
- `tal_maria_ikea-ddj`: Add startup invariants for unique subagent model routing IDs.
- `tal_maria_ikea-hni`: Add doc/test guardrails for tool inventory and prompt wiring drift.
- `tal_maria_ikea-fhu`: Update build-graph-agent skill with web integration acceptance checks.

## Notes
This report is evidence-based from repository commit history and file-level diffs in:
- `src/ikea_agent/chat/subagents/`
- `src/ikea_agent/chat_app/main.py`
- `ui/src/app/subagents/`
- `ui/src/app/api/subagents/`
- `tests/chat/test_api.py`
