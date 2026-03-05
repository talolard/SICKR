# 5. Evaluation Set and Retrieval Quality Loop

## Objective

Generate and curate a 200-query labeled evaluation set with a structured Gemini-assisted workflow, then use it to tune retrieval quality.

## Where Work Happens

- `data/eval/` for query sets, labels, and frozen fixtures.
- `src/ikea_agent/eval/` for metrics runner and reporting logic.
- `tests/eval/` for deterministic metric checks.
- `docs/` for interpretation and decision notes.

## Tasks

- Build an eval-set generation tool (not ad-hoc manual authoring):
  - Take explicit data slices/subsets as input.
  - Take a versioned prompt template as input.
  - Use Gemini (non-embedding model) to generate candidate queries using structured output.
- Persist generation provenance in the database:
  - Prompt registry table with prompt text/template hash and version metadata.
  - Data-subset registry table with slice definition/hash and source timestamp.
  - Generated query table linked by foreign keys to prompt and subset records.
- Curate to final eval dataset (target 200 queries):
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

- Tooling and schema for structured Gemini-based eval-query generation.
- Versioned 200-query eval set with provenance links to prompt and subset records.
- Eval runner and metric report output format.
- Decision note selecting a default strategy for Phase 1 demo.

## Exit Criteria

- Metrics are reproducible.
- Eval query provenance is queryable (prompt version + source subset traceability).
- Default strategy chosen using measured results, not ad-hoc inspection.
- Known weak query patterns are documented for future phases.
