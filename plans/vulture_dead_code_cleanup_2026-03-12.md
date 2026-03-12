# Vulture Dead Code Cleanup

## Goal

Reduce the repo's real dead-code surface without teaching Vulture the wrong lessons.

## Findings From The Baseline `uvx vulture src .` Run

- The raw scan is dominated by noise from `legacy/` and Alembic migrations.
- FastAPI route handlers, pytest fixtures, Pydantic validators, and model fields are reported as unused because their call sites are framework-driven.
- A smaller set of plain helpers and compatibility aliases appear genuinely unreferenced.

## Approach

1. Add repo-local Vulture config that scans only active runtime code plus tests.
2. Ignore decorator-driven endpoints, validators, and fixtures.
3. Keep a small whitelist for schema fields, SQLAlchemy symbols, and explicit compatibility shims that Vulture cannot infer.
4. Delete only helpers with no repo references and no framework reason to exist.
5. Re-run Vulture after each deletion round until only intentional keepers remain.

## Candidate Deletions For The First Pass

- Prompt-loading aliases and CLI parsing helper in `src/ikea_agent/chat/agents/common.py`
- Unused SVG preview helper in `src/ikea_agent/chat/agents/shared.py`
- Backward-compatibility `subagent_*` aliases plus the unused `default_market` setting in `src/ikea_agent/config.py`
- Duplicate retrieval conversion helper in `src/ikea_agent/shared/types.py`
- Unused scene-store `clear()` API in `src/ikea_agent/tools/floorplanner/scene_store.py`
- Unused depth-request adapter in `src/ikea_agent/tools/image_analysis/tool.py`

## Keepers For This Task

- `legacy/` support helpers still imported by reference-only scripts
- `load_archived_all_messages_json`, which is documented as staged-but-not-exposed resume plumbing
- Framework-defined model, ORM, and response-schema fields
