# Eval Runbook

## Generate Queries (Gemini Structured Output)
```bash
make eval-generate
```

Default values:
- `EVAL_SUBSET_ID=phase1_de_v1`
- `EVAL_PROMPT_VERSION=p1_v1`
- `EVAL_TARGET_COUNT=200`
- `EVAL_BATCH_SIZE=25`
- `EVAL_PARALLELISM=4`
- `EVAL_MAX_ROUNDS=8`

## Label Queries
Insert expected canonical product keys in `app.eval_labels` with `relevance_rank` values (1..3).
For local bootstrap, use:
```bash
make eval-labels
```

## Run Metrics
```bash
uv run python -m ikea_agent.eval.run --index-run-id latest --k 10
```

## Reset Eval Data (Phase 2 schema refresh)
```sql
DELETE FROM app.eval_runs;
DELETE FROM app.eval_labels;
DELETE FROM app.eval_queries_generated;
DELETE FROM app.eval_subset_registry;
DELETE FROM app.eval_prompt_registry;
```

## Stored Artifacts
- Prompts: `app.eval_prompt_registry`
- Data slices: `app.eval_subset_registry`
- Generated queries: `app.eval_queries_generated`
- Labels: `app.eval_labels`
- Metric snapshots: `app.eval_runs`

## Metrics
- `Hit@k`
- `Recall@k`
- `MRR`

## Notes
- Query generation uses Gemini JSON-schema constrained output.
- Query generation runs in concurrent batched requests with progress logs per round and per batch.
- Retrieval metric run calls live retrieval service and therefore depends on available embeddings.
