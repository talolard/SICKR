# 6. Integration Hardening and Phase Exit

## Objective
Tie together data modeling, indexing, retrieval, and Django UI into a repeatable local workflow.

## Where Work Happens
- `docs/` for final runbook and phase status.
- `tests/` for end-to-end and smoke checks.
- `scripts/` for orchestration commands that chain DB/index/web/eval.

## Tasks
- Build end-to-end runbook:
  - Rebuild DB/model tables.
  - Run embeddings job.
  - Start Django app.
  - Run eval suite.
- Add regression checks:
  - Smoke tests for retrieval contract and UI response.
  - Schema/docs consistency checks.
- Final documentation pass:
  - Update docs index with Phase 1 workflow links.
  - Capture operational constraints and known risks.
- Phase review:
  - Confirm all Phase 1 exit criteria from prior task files are met.
  - Capture explicit carry-over backlog for Phase 2.

## Deliverables
- Single operator runbook for full local demo.
- Final Phase 1 status summary (`done`, `partial`, `deferred`).
- Prioritized next-step list for Phase 2 (floor plans + fit constraints).

## Exit Criteria
- Fresh clone can reproduce setup + index + search + eval flow locally.
- Demonstration queries return coherent results.
- Remaining limitations are clearly documented.
