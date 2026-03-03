# Phase 2 Implementation Plan

## Scope
Implement Phase 2 feedback from:
- `spec/phase2/ui_critique.md`
- `spec/phase2/source_notes.md`

including UI workflow refresh, parquet data artifacts, multi-country description rollup, strategy-system removal, retrieval/eval simplification, and docs updates.

## Sequencing
1. Beads setup: create epics/tasks with priorities + dependencies.
2. UI-first slice (web forms/templates/views + retrieval sort plumbing).
3. Data foundation (parquet exports and description-country rollup model).
4. Embedding simplification (single embedding input path, remove strategy infrastructure).
5. Retrieval + eval schema/code alignment after strategy removal.
6. Data/docs cleanup, including eval data purge and runbook refresh.

## Quality Gates
For each subtask completion commit:
- `make format-all`
- `make test`
- `make tidy`

## Tracking
Primary beads issues:
- `tal_maria_ikea-5i3` (UI)
- `tal_maria_ikea-7vf` (data/parquet/rollup)
- `tal_maria_ikea-9iz` (strategy removal)
- `tal_maria_ikea-thz` (retrieval alignment)
- `tal_maria_ikea-xsl` (eval/docs cleanup)
