# Search Agent Eval

This eval measures the search agent's **query decomposition**, not retrieval quality.
The target question is: given an open-ended furnishing request, does the agent issue
good `run_search_graph` tool calls with the right semantic queries, filters, exclusions,
and creative search expansions?

## Scope

In scope:

- decomposition of the user request into one or more `run_search_graph` calls
- whether hard constraints such as budget, dimensions, or exclusions are reflected
- whether the query set covers the anchor need and adjacent solution pieces
- whether the agent makes at least one useful lateral or creative search leap

Out of scope:

- embedding quality
- reranking quality
- retrieval relevance
- database or index correctness

## Current Architecture

The authoritative eval now lives under `evals/`, not `tests/`.
It runs through a direct Python entrypoint and is intentionally independent of pytest.

Files:

- [`evals/search/dataset.py`](../evals/search/dataset.py)
  Defines the cases and the evaluators.
- [`evals/search/harness.py`](../evals/search/harness.py)
  Runs the real search agent with injected toolset services.
- [`evals/search/run.py`](../evals/search/run.py)
  CLI runner for live eval execution.
- [`evals/base/harness.py`](../evals/base/harness.py)
  Shared eval primitives, including the Logfire-backed tool-call judge wrapper.
- [`evals/base/capture.py`](../evals/base/capture.py)
  Shared helpers for extracting tool-call payloads from spans or messages.

## How The Eval Works

The eval runs the real `build_search_agent()` prompt and model path.
It does not monkeypatch module globals and it does not run through pytest.

Instead it uses two explicit seams:

1. Toolset dependency injection

The search toolset now accepts a small `SearchToolsetServices` dataclass.
The eval injects a stub `run_search_batch` implementation so the agent can call
`run_search_graph` without needing Milvus, embeddings, or DuckDB.

2. Native Logfire / PydanticAI spans

The eval uses `configure_logfire(...)` and native `logfire.instrument_pydantic_ai()`
instrumentation from the runtime.
The judge reads `run_search_graph` calls from the recorded span tree rather than from
patched globals or bespoke transcript scraping.

That gives the eval:

- real model behavior
- real tool invocation semantics
- concurrency-safe capture
- no pytest-only harness
- no module-global monkeypatch

## Evaluators

The dataset uses two evaluators:

1. `HasMatchingSpan(...)`

Asserts that the run actually emitted a `run_search_graph` tool span.

2. `LogfireToolCallLLMJudge(...)`

Wraps a normal `LLMJudge`, but replaces the grading surface with a synthetic output
containing the `run_search_graph` calls extracted from the span tree.

This means the judge sees:

- the user message
- the expected attributes
- the actual captured tool-call payloads
- the final assistant text for context

## Stubbed Runtime Model

The eval harness uses a minimal runtime stub plus injected toolset services.

Important details:

- search execution is replaced at the toolset seam, not by patching imports
- persistence repositories are disabled for the eval run
- attachment storage uses a temp directory per case
- a tiny catalog stub exists only so unexpected bundle calls do not crash the run

This keeps the eval focused on query planning while preserving the actual agent and toolset flow.

## Running The Eval

Prerequisites:

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- network access to the configured model backend

Run:

```bash
uv run python -m evals.search.run
```

Verbose mode:

```bash
uv run python -m evals.search.run --verbose
```

Optional concurrency override:

```bash
uv run python -m evals.search.run --max-concurrency 2
```

The runner will:

- set `ALLOW_MODEL_REQUESTS=1` if it is not already set
- configure logging
- configure native Logfire / PydanticAI instrumentation
- execute the dataset directly
- print the report
- exit non-zero if any assertion fails

## Why This Lives Outside Pytest

Prompt and model evals are not the same thing as deterministic unit tests.
They have different ergonomics, different failure modes, and different runtime needs.

This repo now treats them separately:

- `tests/` is for deterministic pytest coverage
- `evals/` is for direct, live, model-facing evaluation harnesses

Deterministic tests still exist for the shared helpers and toolset seams, but the eval itself
is not a pytest test.

## Extending The Dataset

Add new cases in [`evals/search/dataset.py`](../evals/search/dataset.py).

Keep `expected_attributes` focused on:

- concrete must-have constraints
- required product categories or adjuncts
- meaningful exclusions
- one or two creative reasoning expectations

Avoid turning the rubric into an exact string template.
The judge should grade whether the query set solves the request well, not whether it matches a single phrasing.
