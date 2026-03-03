# 5. Evaluation Set and Retrieval Quality Loop

## Objective
Create a 200-query labeled evaluation set and use it to tune text-construction and retrieval quality.

## Where Work Happens
- `data/eval/` for query sets, labels, and frozen fixtures.
- `src/tal_maria_ikea/eval/` for metrics runner and reporting logic.
- `tests/eval/` for deterministic metric checks.
- `docs/` for interpretation and decision notes.

## Tasks
- Build eval dataset (200 Germany-focused queries):
  - Include category, style, dimension-sensitive, and ambiguous intents.
  - For each query, label expected top 2-3 products (or acceptable set).
- Define quality metrics:
  - Recall@k and hit@k for expected items.
  - Optional MRR for rank quality.
- Create repeatable eval runner:
  - Executes queries against current index/retrieval version.
  - Writes metric snapshots per run.
- Run comparisons across embedding text strategies:
  - Baseline vs enriched metadata-first text.
  - Record tradeoffs and winner.

## Deliverables
- Versioned 200-query eval set.
- Eval runner and metric report output format.
- Decision note selecting a default strategy for Phase 1 demo.

## Exit Criteria
- Metrics are reproducible.
- Default strategy chosen using measured results, not ad-hoc inspection.
- Known weak query patterns are documented for future phases.
