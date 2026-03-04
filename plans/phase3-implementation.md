# Phase 3 Implementation Sequencing

Plan source documents:

- `spec/phase3/current_architecture.md`
- `spec/phase3/phase3_implementation_plan.md`
- `spec/phase3/spec_notes.md`

## Ordered Steps

1. Foundation: create DuckDB Phase 3 schema and repositories for telemetry/conversation/feedback.
2. Config plane: add Django admin models for prompt templates, variant sets, reason tags, and expansion policy.
3. Retrieval extension: add query expansion and reranking service pipeline with request/result snapshots.
4. Prompt generation: add parallel prompt-variant execution and structured summary parsing.
5. UX flows: implement prompt lab, conversation screens, rerank diff page, and search controls.
6. Hardening: full tests, docs updates, and quality gates.

## Quality Gates

- `make format-all`
- `make test`
- `make tidy`

## Tracking

Track work in beads under a dedicated Phase 3 epic with one task per major workstream.
