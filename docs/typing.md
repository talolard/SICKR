# Typing and Pyrefly Policy

## Goal
Keep type checking strict, deterministic, and agent-safe as Phase 1 modules (`ingest`, `retrieval`, `web`, `eval`, `shared`) are added.

## Current Configuration
The project uses `pyrefly.toml` (not `pyproject.toml`) as the canonical type-check config.

Key policy choices:
- Explicit `project-includes` for `src/**/*.py` and `tests/**/*.py`.
- Explicit `search-path = ["src"]` with `disable-search-path-heuristics = true` for deterministic imports.
- `untyped-def-behavior = "check-and-infer-return-type"` to keep untyped bodies checked.
- No permissive import fallbacks: `replace-imports-with-any = []`, `ignore-missing-imports = []`.
- Ignore directives limited to `# type: ignore` and `# pyrefly: ignore`.
- `strict-callable-subtyping = true` to avoid broad `*args/**kwargs` callable compatibility.

## Quality Gate
- `make typecheck` runs `uv run pyrefly check`.
- `make tidy` includes `uv run pyrefly check` before tests.

## Change Rules
When introducing new packages under `src/` or `tests/`, keep them in-scope for pyrefly by default.
Only add relaxations (e.g., missing-import allowlists or sub-config overrides) with a documented reason in this file.

## Package Conventions
- Put cross-module contracts in `src/tal_maria_ikea/shared/types.py`.
- Keep SQL in `sql/` and call it from typed repository/service modules.
- Keep CLI entrypoints small and delegate to typed orchestration functions.
