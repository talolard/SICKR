# Phase 1 Status

## Status Matrix
- Data audit/modeling: `done` (SQL schema/modeling and profile scripts added)
- Embedding pipeline: `done` (sync-first parallel indexer + run metadata)
- Retrieval service: `done` (semantic retrieval + structured filters + query logging)
- Django web app: `done` (search UI + filters + global shortlist)
- Eval loop: `done` (Gemini structured generation + metrics runner + registries)
- Integration hardening: `partial` (runbook/scripts/tests in place, live API flows depend on credentials)

## Deferred to Phase 2
- Floor plan upload and fit constraints
- Multi-user shortlist identity/auth model
- Currency normalization for non-EUR markets
