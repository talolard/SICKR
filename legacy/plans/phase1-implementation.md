# Phase 1 Full Implementation Plan

## Goal
Implement the complete Phase 1 scope described in `spec/phase1/index.md` across data modeling, indexing, retrieval, web UI, eval, and integration tooling.

## Sequence
1. [x] Data + DB modeling SQL and docs
2. [x] Shared typed contracts and config expansion
3. [x] Ingest/index pipeline + CLI
4. [x] Retrieval service + SQL
5. [x] Django web app + shortlist persistence
6. [x] Eval generation + metrics runner
7. [x] Integration scripts, docs, and test coverage

## Validation Gate
- `make format-all`
- `make test`
