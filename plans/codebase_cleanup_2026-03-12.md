# Codebase Cleanup Plan

## Goal

Remove stale compatibility layers and documentation drift, consolidate duplicated agent wiring, and split the largest backend/UI hotspots without changing user-visible behavior.

## Workstreams

1. Documentation source-of-truth pass
   - Update `README.md`, `docs/web.md`, and related docs so they describe the current plain `pydantic_ai.Agent` runtime rather than `pydantic-graph`.
   - Fix broken links in `docs/index.md` (`docs/pipeline.md`, `docs/phase1_status.md`) by either restoring those docs or removing the references.
   - Audit the docs index for active-but-unlisted docs such as `docs/image_analysis_tools.md`, `docs/gcp_setup.md`, and `docs/codex_multi_agent_workflow.md`, then either index or archive them.
   - Definition of done: active docs agree on the runtime shape and `docs/index.md` has no broken links.

2. Dead helper and compatibility-alias removal
   - Remove unused helpers from `src/ikea_agent/shared/parsing.py` after confirming no live imports remain.
   - Remove the single-query compatibility wrapper in `src/ikea_agent/chat/search_pipeline.py` if all callers can use the batch API directly.
   - Delete `preview_svg_data_uri()` from `src/ikea_agent/chat/agents/shared.py`.
   - Remove backward-compat aliases from `src/ikea_agent/chat/agents/common.py` and keep one prompt-loading path.
   - Definition of done: the cited helpers no longer exist, imports are simplified, and targeted tests cover the surviving APIs.

3. Agent registry consolidation
   - Make `src/ikea_agent/chat/agents/index.py` the only source of truth for agent metadata, builders, and any per-agent runtime hooks needed by the app.
   - Remove duplicated agent-specific branching from `src/ikea_agent/chat_app/main.py`, especially around AG-UI app construction and dependency wiring.
   - Add a small typed interface for per-agent dependency construction if `main.py` still needs agent-specific runtime objects.
   - Definition of done: app wiring consumes the registry instead of re-declaring agent knowledge.

4. Backend hotspot decomposition
   - Split `src/ikea_agent/chat_app/main.py` into focused modules for route registration and AG-UI bootstrapping.
   - Keep one thin app-factory entrypoint in `main.py`; move attachment, comment, trace, catalog, generated-image, OpenUSD, thread-data, and AG-UI wiring into dedicated modules.
   - Preserve route paths and response contracts exactly while moving code.
   - Definition of done: `main.py` becomes orchestration-only and the extracted modules are independently testable.

5. UI renderer hotspot decomposition
   - Split `ui/src/components/copilotkit/CopilotToolRenderers.tsx` into smaller typed units:
     - parse/normalization helpers
     - tool-specific render bridges
     - renderer registration shell
   - Keep tool names and renderer behavior stable so AG-UI replays and retries remain idempotent.
   - Add or tighten unit tests around extracted renderers, especially floor-plan, bundle, and image-output flows.
   - Definition of done: the top-level renderer file is a small registry component instead of a mixed parser/renderer bundle.

6. Reranker configuration alignment
   - Resolve the mismatch where the default `transformer` backend is configured in `src/ikea_agent/config.py` but `pyproject.toml` does not declare the transformer runtime dependencies.
   - Either:
     - add the required optional/runtime dependencies plus startup/docs guardrails, or
     - switch the default backend to one that matches the installed dependency set.
   - Decide whether `rerank_candidate_limit` should be wired into the retrieval/rerank flow or removed from settings, docs, and tests.
   - Definition of done: config defaults, installed dependencies, and runtime behavior agree.

7. Stale tracked bootstrap and history docs cleanup
   - Remove or archive `init.md`, `init2.md`, `docs/floorplan_svg_migration_progress.md`, and `docs/ui_copilotkit_milestone_status.md` after preserving any still-relevant operational guidance elsewhere.
   - Keep planning history under `plans/` and active runbooks under `docs/`; avoid task handoff logs in the docs root.
   - Finish with a docs index sweep so archived material is no longer presented as active guidance.
   - Definition of done: the docs tree contains current runbooks/reference material, and historical scaffolding lives outside the active docs surface.

## Recommended Order

1. Fix documentation drift and broken links first so the repository describes the current architecture accurately.
2. Remove dead helpers and compatibility aliases next to shrink the active surface area before larger refactors.
3. Consolidate the agent registry before splitting `chat_app/main.py` so the extraction lands on one stable source of truth.
4. Split the backend and UI hotspots once the ownership boundaries are clear.
5. Align reranker config and dependency defaults after the retrieval surface is simpler.
6. Archive or delete stale bootstrap/history docs at the end, then do one final docs index pass.

## Guardrails

- Keep route paths, tool names, and JSON contracts stable during the cleanup.
- Treat `legacy/` as reference-only; do not move active runtime code there.
- Prefer incremental PRs by workstream instead of one broad cleanup branch.

## Validation

- `rg -n "pydantic-graph|Chat Graph|graph runtime|pydantic-ai web UI" README.md docs src/ikea_agent`
- `uv run pytest tests/chat tests/tools -q`
- `cd ui && pnpm test -- --runInBand`
- `make tidy`
- `make ui-test-e2e-real-ui-smoke` for any change that affects agent routing, AG-UI mounting, or tool rendering behavior
