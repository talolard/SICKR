# Eval Runbook

## Generate Queries (Gemini Structured Output)
```bash
uv run python -m tal_maria_ikea.eval.generate \
  --subset-id phase1_de_v1 \
  --prompt-version p1_v1 \
  --target-count 200
```

## Label Queries
Insert expected canonical product keys in `app.eval_labels` with `relevance_rank` values (1..3).

## Run Metrics
```bash
uv run python -m tal_maria_ikea.eval.run --index-run-id latest --k 10
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
- Retrieval metric run calls live retrieval service and therefore depends on available embeddings.
