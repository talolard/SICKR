# Mark 17 Search Agent Behavior Corrections

## Summary

Implement the search-agent behavior fixes for epic `tal_maria_ikea-1iw.22` on top of the closed Mark 17 guardrail branches:

- `tal_maria_ikea-1iw.20` runtime/default-model guardrails
- `tal_maria_ikea-1iw.21` search eval expansion and fixture coverage

The change set should make the agent treat the IKEA catalog as broad rather than lighting-only, prevent unsupported workaround bundles, and improve follow-through on complementary products when they are grounded in retrieval results.

## Why We Need This

Tal's feedback from thread `agent_search-286fe4b8` highlighted three distinct failures:

1. The agent claimed the catalog was effectively lighting-focused.
2. The agent suggested unsupported solutions and workarounds when it could not ground them.
3. The agent reasoned about complementary placement or support products but did not consistently follow through on them in the surfaced solution.

The trace investigation for task `tal_maria_ikea-1iw.17` did not recover the original run payload locally:

- repo-local DuckDB copies do not contain `agent_search-286fe4b8`
- a later Logfire-backed UI lookup on March 17, 2026 showed `GET /api/threads/agent_search-286fe4b8` returning `404`
- that same lookup returned no saved bundle proposals

That means the exact historical model reasoning is not recoverable from persisted thread state. The fix therefore needs to rely on the captured user-visible failure quotes plus the guardrail eval cases from `tal_maria_ikea-1iw.21`, while keeping the investigation notes explicit about the missing decisive trace.

## Goals

- Update the search-agent prompt so it explicitly treats the IKEA catalog as broad.
- Clarify that the agent can use phrase-like and keyword-like search phrasing in addition to semantic retrieval.
- Add runtime enforcement so `propose_bundle` can only use products that were actually returned by `run_search_graph`.
- Make the prompt explicitly require follow-through on grounded complementary products.
- Keep the change aligned with the hallway/complementary/no-bundle eval cases added in `evals/search/`.

## Non-Goals

- Rebuild the missing historical thread archive.
- Redesign retrieval, reranking, or catalog ingestion.
- Add new UI rendering surfaces.
- Rework the already-closed Mark 17 runtime-default or eval-expansion epics.

## Core Design Decisions

### 1. Treat the trace investigation as partially recoverable, not decisive

We have enough trace evidence to state that the persisted thread was unavailable during later inspection, but not enough to reconstruct the original model span tree. The implementation should record that limit rather than over-claiming a root cause.

### 2. Enforce bundle grounding in runtime, not only in prompt text

The prompt already says bundle items must come from grounded tool results, but there is no runtime enforcement. This epic should add a typed state surface that remembers grounded product IDs from search results and rejects bundle items that were never returned.

### 3. Use prompt changes for scope framing and follow-through behavior

Catalog breadth, phrase/keyword search guidance, and complementary-product follow-through are model-behavior instructions. Those should stay in the search prompt and be covered by prompt-focused tests plus the existing eval dataset.

## Deliverables

- Search-agent prompt updates in `src/ikea_agent/chat/agents/search/prompt.md`
- Runtime/state grounding changes in:
  - `src/ikea_agent/chat/agents/state.py`
  - `src/ikea_agent/chat/agents/search/toolset.py`
  - `src/ikea_agent/shared/types.py` if new typed search-state payloads are needed
- Updated tests/evals
- Documentation update describing grounded bundle enforcement and the investigation outcome

## Sequencing

1. Record the investigation outcome and limits.
2. Add typed runtime grounding support for search results.
3. Update prompt instructions for catalog breadth, grounded complementary follow-through, and no unsupported workarounds.
4. Extend unit coverage and, where needed, eval/docs coverage.
5. Run `make tidy` and `make ui-test-e2e-real-ui-smoke`.

## Acceptance Criteria

- The search prompt explicitly states broad catalog access and phrase/keyword-aware search behavior.
- `propose_bundle` rejects ungrounded product IDs.
- Search-agent tests cover the new prompt and runtime behavior.
- Docs mention the grounded-bundle rule and the limited investigation outcome for `agent_search-286fe4b8`.
