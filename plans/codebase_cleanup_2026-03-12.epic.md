# Epic: Codebase cleanup and runtime surface consolidation

## Summary

Clean up stale compatibility layers, documentation drift, and oversized backend/UI modules without changing user-visible behavior.

This epic turns the cleanup plan in `plans/codebase_cleanup_2026-03-12.md` into an execution-ready work graph:

- fix docs so the repo describes the current `pydantic_ai.Agent` runtime accurately
- remove dead helpers and backwards-compatibility aliases that expand the active surface area
- consolidate agent metadata and runtime wiring so the app has one source of truth
- split backend and UI hotspots into smaller typed modules with stable external contracts
- align reranker defaults with the installed dependency set and the actual retrieval flow
- archive stale bootstrap/history material so active docs stay current

The work should land as incremental PRs or stacked PRs by workstream, not as one broad cleanup branch.

## Why We Need This

The current repo still carries several forms of drift:

- docs describe old runtime shapes and contain broken or stale index entries
- helper modules expose compatibility paths that no longer reflect how the runtime works
- agent wiring knowledge is split across the agent registry and `chat_app/main.py`
- the biggest backend and UI files mix orchestration, parsing, rendering, and transport concerns
- reranker configuration defaults do not obviously match installed dependencies
- historical bootstrap/status notes still appear in active docs surfaces

That drift makes future implementation slower and less safe. Workers must rediscover which path is canonical before they can make changes, and reviewers have to reason about multiple overlapping sources of truth.

## Goals

1. Make the docs tree accurately describe the current runtime architecture.
2. Remove stale helper APIs and compatibility aliases after confirming the live API surface.
3. Make `src/ikea_agent/chat/agents/index.py` the only source of truth for agent metadata/builders and related runtime hooks.
4. Split `src/ikea_agent/chat_app/main.py` into orchestration plus focused modules while preserving all external contracts.
5. Split `ui/src/components/copilotkit/CopilotToolRenderers.tsx` into smaller typed units without changing tool replay behavior.
6. Make reranker defaults, dependencies, docs, and tests agree.
7. Keep active docs current by archiving or relocating stale bootstrap/history material.

## Non-Goals

- Do not change route paths, JSON contracts, or tool names.
- Do not move active runtime code into `legacy/`.
- Do not redesign agent behavior or CopilotKit semantics as part of cleanup.
- Do not bundle unrelated product work into this epic.
- Do not collapse the entire cleanup into one unreviewable PR.

## Core Design Decisions

### 1. Documentation alignment lands first

The repo should describe the current architecture before deeper refactors continue. This reduces the risk that cleanup workers preserve obsolete behavior because the docs still imply it is required.

### 2. Remove dead compatibility layers before larger extractions

Dead helpers and alias paths increase the surface area of any later refactor. Confirm they are unused, delete them, then let later work target the surviving canonical APIs only.

### 3. Registry consolidation precedes backend module extraction

`src/ikea_agent/chat/agents/index.py` must own agent metadata/builders and any small typed runtime-hook surface before `chat_app/main.py` is split. Otherwise the extraction just moves duplicated branching into new files.

### 4. Backend and UI decompositions must preserve behavior exactly

These tasks are structural cleanups, not product changes. The contract is stable routes, stable tool names, stable response shapes, and idempotent AG-UI replay behavior.

### 5. The reranker task must end with one explicit supported story

The current plan leaves two allowed outcomes:

- keep `transformer` as the default and add the required dependency/runtime guardrails
- switch the default to a backend that matches the installed dependency set

Either outcome is acceptable, but the task is not done until config defaults, docs, tests, and runtime behavior all tell the same story. The same applies to `rerank_candidate_limit`: wire it through clearly or remove it completely.

### 6. Historical material moves out of the active docs surface

Operational docs belong in `docs/`. Planning history belongs in `plans/`. Old bootstrap/status notes should be archived or removed once any still-relevant guidance is preserved elsewhere.

## Component Breakdown

### Documentation surface

Responsibilities:
- update runtime descriptions in `README.md`, `docs/web.md`, and `docs/index.md`
- fix or remove broken doc references
- ensure active docs are indexed and stale docs are not presented as current guidance

Why it exists:
- the repo needs one coherent active docs surface before and after cleanup

### Runtime API surface

Responsibilities:
- remove dead helpers in `src/ikea_agent/shared/parsing.py`
- remove the single-query compatibility wrapper in `src/ikea_agent/chat/search_pipeline.py` if callers can use the batch API directly
- remove `preview_svg_data_uri()` from `src/ikea_agent/chat/agents/shared.py`
- keep one prompt-loading path in `src/ikea_agent/chat/agents/common.py`

Why it exists:
- smaller canonical APIs make later refactors safer and easier to review

### Agent registry and backend bootstrapping

Responsibilities:
- consolidate agent metadata and builders in `src/ikea_agent/chat/agents/index.py`
- add a small typed per-agent dependency construction interface if runtime-specific objects are still needed
- extract route and AG-UI wiring out of `src/ikea_agent/chat_app/main.py`

Why it exists:
- runtime ownership boundaries should be explicit and centralized

### UI renderer surface

Responsibilities:
- split parser/normalization helpers, tool-specific bridges, and registry wiring from `ui/src/components/copilotkit/CopilotToolRenderers.tsx`
- preserve idempotent rendering keyed by `tool_call_id`
- tighten tests around floor-plan, bundle, and image-output flows

Why it exists:
- the current file mixes concerns that should be independently testable

### Retrieval and config surface

Responsibilities:
- align reranker defaults, dependency declarations, runtime guardrails, and tests
- decide the fate of `rerank_candidate_limit`

Why it exists:
- config defaults must reflect what the runtime can actually support

## Ownership Model

- `epic_writer`: produces the breakdown, dependencies, and merge-readiness structure.
- `epic_worker`: owns one implementation branch/worktree for this epic and carries the work to PR-ready state.
- `pr_reviewer` or human reviewer: reviews cleanup risk, especially contract-preservation claims and docs drift.
- `merge_coordinator`: merges the queued merge-request item from `tal_maria_ikea-0uk` after checks are green and closes the queue item after post-merge verification.

## Conflict Analysis And Resolutions

### Docs cleanup versus docs archival

Conflict:
- some docs need to be corrected immediately, while others should be archived or removed later

Resolution:
- separate the first-pass runtime/docs alignment from the final stale-doc archival sweep
- the final archival task depends on the implementation tasks so it can reflect the final repo shape

### Registry consolidation versus `main.py` extraction

Conflict:
- extracting `main.py` first can freeze current duplication into new modules

Resolution:
- the registry consolidation task lands first and defines the typed runtime hook surface used by the later extraction

### Structural cleanup versus behavior drift

Conflict:
- the backend/UI hotspot tasks could accidentally change route behavior, tool names, or AG-UI replay semantics

Resolution:
- each task definition of done explicitly requires stable external behavior and targeted tests
- the epic readiness gate requires `make ui-test-e2e-real-ui-smoke` if routing, AG-UI mounting, or renderer behavior changes

### Reranker ambiguity

Conflict:
- the cleanup plan allows more than one valid end state for reranker defaults

Resolution:
- keep the allowed options explicit in the task description, but require one final supported story with matching config, dependency declarations, docs, and tests

## Deliverables

- updated cleanup execution record in `plans/codebase_cleanup_2026-03-12.epic.md`
- Beads epic with child implementation tasks and readiness dependencies
- corrected active docs/index entries
- deleted dead helper/compatibility code paths
- consolidated agent registry/runtime hook surface
- extracted backend route and AG-UI modules
- extracted UI renderer helper/bridge/registry modules
- aligned reranker configuration/dependency story
- archived or removed stale bootstrap/history docs plus a final docs index sweep

## Sequencing

### Phase 1: Docs truth

- align runtime docs and repair the docs index

### Phase 2: Surface-area reduction

- remove dead helpers and compatibility aliases

### Phase 3: Backend ownership cleanup

- consolidate the agent registry
- split `chat_app/main.py` around the consolidated registry contract

### Phase 4: UI ownership cleanup

- split Copilot tool renderers into typed units and lock renderer behavior with tests

### Phase 5: Config/runtime alignment

- resolve reranker default/dependency mismatch and settle the settings surface

### Phase 6: Archive stale history and close out

- archive/remove stale bootstrap/history docs
- do a final docs index sweep
- run the epic readiness gate and queue merge handling

## Beads Breakdown

### Epic

- `Codebase cleanup and runtime surface consolidation`

### Implementation tasks

1. `Align runtime docs and repair the active docs index`
   - Scope:
     - update `README.md`, `docs/web.md`, and related docs to describe the current `pydantic_ai.Agent` runtime
     - fix broken links in `docs/index.md`
     - index or archive active-but-unlisted docs where appropriate
   - Definition of done:
     - active docs agree on the runtime shape
     - `docs/index.md` has no broken links
     - the updated docs make the later cleanup tasks easier to review

2. `Remove dead helpers and compatibility aliases`
   - Depends on:
     - `Align runtime docs and repair the active docs index`
   - Scope:
     - remove stale helpers/aliases from the parsing/search/shared/common modules named in the source plan
     - update imports and targeted tests around the surviving APIs
   - Definition of done:
     - the cited helpers/aliases no longer exist
     - callers use the canonical surviving path
     - targeted tests cover the surviving API surface

3. `Consolidate agent registry ownership and typed runtime hooks`
   - Depends on:
     - `Remove dead helpers and compatibility aliases`
   - Scope:
     - make `src/ikea_agent/chat/agents/index.py` the sole source of truth for metadata/builders
     - add a typed per-agent dependency construction interface if needed by the app
     - remove agent-specific duplication from `src/ikea_agent/chat_app/main.py`
   - Definition of done:
     - registry consumers stop re-declaring agent knowledge
     - any remaining per-agent runtime object construction is typed and centralized

4. `Extract focused backend modules from chat_app/main.py`
   - Depends on:
     - `Consolidate agent registry ownership and typed runtime hooks`
   - Scope:
     - move route registration and AG-UI bootstrapping into focused modules
     - keep `main.py` as a thin orchestration entrypoint
   - Definition of done:
     - extracted modules cover attachment, comment, trace, catalog, generated-image, OpenUSD, thread-data, and AG-UI wiring as needed
     - route paths and response contracts remain unchanged
     - the extracted modules are independently testable

5. `Split Copilot tool renderer registry into typed units`
   - Depends on:
     - `Remove dead helpers and compatibility aliases`
   - Scope:
     - split normalization helpers, tool-specific render bridges, and registry wiring out of `ui/src/components/copilotkit/CopilotToolRenderers.tsx`
     - tighten unit tests around floor-plan, bundle, and image-output flows
   - Definition of done:
     - the top-level file is a small registry shell
     - renderer behavior and tool names remain stable across replays/retries
     - tests cover the extracted flows and empty/error cases where relevant

6. `Align reranker defaults, dependencies, and settings semantics`
   - Depends on:
     - `Extract focused backend modules from chat_app/main.py`
     - `Split Copilot tool renderer registry into typed units`
   - Scope:
     - resolve the `transformer` default/dependency mismatch
     - either wire `rerank_candidate_limit` through the retrieval/rerank flow or remove it from config/docs/tests
   - Definition of done:
     - the repo has one supported reranker story
     - config defaults, dependency declarations, docs, and tests agree
     - startup/docs guardrails exist if optional dependencies remain optional

7. `Archive stale bootstrap/history docs and finish the final docs sweep`
   - Depends on:
     - `Align runtime docs and repair the active docs index`
     - `Extract focused backend modules from chat_app/main.py`
     - `Split Copilot tool renderer registry into typed units`
     - `Align reranker defaults, dependencies, and settings semantics`
   - Scope:
     - remove or archive `init.md`, `init2.md`, `docs/floorplan_svg_migration_progress.md`, and `docs/ui_copilotkit_milestone_status.md` after preserving any still-relevant guidance elsewhere
     - finish the docs index sweep so archived material is not presented as active guidance
   - Definition of done:
     - active docs contain current runbooks/reference material only
     - historical scaffolding lives outside the active docs surface

### Readiness gate

8. `Validate codebase cleanup branch against repo quality gates`
   - Depends on:
     - all implementation tasks above
   - Scope:
     - run targeted backend and UI tests for changed surfaces
     - run `make tidy`
     - run `make ui-test-e2e-real-ui-smoke` if routing, AG-UI mounting, or tool-rendering behavior changed
     - confirm docs/index links and preserved external contracts
   - Definition of done:
     - validations are recorded in the bead
     - any remaining risk is documented explicitly
     - the branch is ready to queue for merge handling

### Merge handling

9. `Queue merge-request for cleanup epic once checks are green`
   - Parent:
     - `tal_maria_ikea-0uk` (`awaiting-merge`)
   - Depends on:
     - all implementation tasks
     - `Validate codebase cleanup branch against repo quality gates`
   - Scope:
     - create/update the merge-request queue item with branch, PR, validation summary, and risk notes
     - keep it `status=blocked`, `assignee=merger-agent`, and `type=merge-request` (or `label=merge-request` fallback only if the CLI rejects the type)
   - Definition of done:
     - the branch/PR is queued for merge coordination with enough context for a merge-only session to act

## Acceptance Criteria

- Active docs describe the current runtime accurately and the docs index has no broken active references.
- The named dead helpers and compatibility aliases are removed, and the remaining API surface is covered by targeted tests.
- `src/ikea_agent/chat/agents/index.py` is the sole source of truth for agent metadata/builders and any related runtime hook surface.
- `src/ikea_agent/chat_app/main.py` is orchestration-only, with extracted focused modules preserving all existing route contracts.
- `ui/src/components/copilotkit/CopilotToolRenderers.tsx` is reduced to a small registry shell with stable renderer behavior and tests around the extracted flows.
- Reranker defaults, dependency declarations, docs, and runtime behavior all agree.
- Stale bootstrap/history docs no longer appear as active guidance.
- Repo-required validation passes before merge queue handoff.

## Explicit Review Gate

Before the merge-request item is queued under `tal_maria_ikea-0uk`, review must confirm:

- route paths, JSON contracts, and tool names stayed stable
- AG-UI replay/idempotency behavior was not regressed by backend or renderer extraction
- the reranker decision is documented clearly enough that future workers do not have to rediscover the intended supported setup

## References

- `plans/codebase_cleanup_2026-03-12.md`
- `README.md`
- `docs/index.md`
- `docs/web.md`
- `src/ikea_agent/chat/agents/index.py`
- `src/ikea_agent/chat_app/main.py`
- `ui/src/components/copilotkit/CopilotToolRenderers.tsx`
