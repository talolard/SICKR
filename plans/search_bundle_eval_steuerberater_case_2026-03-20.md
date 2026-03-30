# Search Bundle Eval: Steuerberater Case

## Goal

Add thread-derived search eval coverage for the saved bundle from
`agent_search-fe0d9f2d`, but only for the bundle-stage continuation slice. The
eval should not replay the whole conversation. It should start from the point
where the prior turn has already established the direction, the user said
`Yes`, and the search agent already re-grounded the chosen products.

## Case Shape

- Reuse the existing `evals/search` framework.
- Extend the harness to support fixture-backed `message_history` plus seeded
  grounded search batches.
- Judge the new cases with `LLMJudge` over the captured `propose_bundle` call,
  not a deterministic rule engine.
- Keep search-query quality evaluators on the search-planning cases only.
- Add a search-call contract so the continuation cases can explicitly forbid
  `run_search_graph`.

## New Continuation Cases

- `steuerberater_workstation_coverage`
- `steuerberater_large_storage_quantity_sanity`
- `steuerberater_storage_role_differentiation`
- `steuerberater_budget_utilization`

All four cases reuse one shared fixture derived from the real thread:

- initial brief for Anna, Hans, and Klaus in one 8m by 6m office
- prior assistant concept response
- user follow-up `Yes`
- grounded re-search batch for the chosen desk, executive chair, BROR unit,
  conference table, conference chair, IDÅSEN cabinet, and HEKTAR lamp

## Validation

- `uv run pytest tests/evaltests/search -q`
