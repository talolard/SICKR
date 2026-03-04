# Phase 1 Status

## Status Matrix
- Data audit/modeling: `done` (SQL schema/modeling and profile scripts added)
- Embedding pipeline: `done` (sync-first parallel indexer + run metadata)
- Retrieval service: `done` (semantic retrieval + structured filters + query logging)
- Chat web runtime: `done` (FastAPI + graph-backed chat UI and typed chat API)
- Eval loop: `done` (Gemini structured generation + metrics runner + registries)
- Integration hardening: `partial` (runbook/scripts/tests in place, live API flows depend on credentials)

## Deferred to Phase 2
- Floor plan upload and fit constraints
- Multi-user shortlist identity/auth model
- Currency normalization for non-EUR markets
