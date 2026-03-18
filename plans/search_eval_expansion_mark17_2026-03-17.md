# Mark 17 Search Eval Expansion Plan

## Summary

Extend the authoritative `evals/search/` harness beyond first-step query decomposition so it can:

- check a user-facing transcript constraint (`bundle` must stay out of assistant prose)
- exercise `propose_bundle` after retrieval using seeded second-step fixtures
- document and support reproducible capture of end-to-end eval runs for fixture authoring
- add thread-grounded omission and no-bundle guards from `agent_search-286fe4b8`

## Design

1. Keep live grading in `evals/search/` on the real agent.
2. Add a seeded retrieval fixture seam so the eval can drive bundle decisions without introducing retrieval infra.
3. Keep search-tool grading span-backed via `run_search_graph`.
4. Add case-specific bundle-tool grading and deterministic conversation-contract checks.
5. Add a separate capture command for task `.9`:
   - live model run
   - transcript tool calls
   - transcript tool returns
   - bundle proposals emitted into shared state

## Out Of Scope

- prompt or behavior fixes from epic `tal_maria_ikea-1iw.22`
- changing the search-agent prompt so these new evals pass
- replacing the existing span-based judge architecture
