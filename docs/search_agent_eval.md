# Search Agent Eval

Quick run:

```bash
uv run python -m evals.search
```

This eval now measures two related behaviors:

- first-step **query decomposition** via `run_search_graph`
- second-step **bundle follow-through** via `propose_bundle` when a scenario benefits from a structured UI bundle

The target question is: given an open-ended furnishing request, does the agent issue
good `run_search_graph` tool calls with the right semantic queries, filters, exclusions,
and creative search expansions, and does it turn grounded retrieval into a coherent
bundle only when it should?

## Scope

In scope:

- decomposition of the user request into one or more `run_search_graph` calls
- bundle follow-through when the case includes seeded retrieval results
- transcript-level response contracts such as forbidden user-facing terms
- whether hard constraints such as budget, dimensions, or exclusions are reflected
- whether the query set covers the anchor need and adjacent solution pieces
- whether the agent makes at least one useful lateral or creative search leap

Out of scope:

- embedding quality
- reranking quality
- retrieval relevance
- database or index correctness
- fixing prompt or behavior failures that the eval exposes

## Current Architecture

The authoritative eval now lives under `evals/`, not `tests/`.
It runs through a direct Python entrypoint and is intentionally independent of pytest.

Files:

- [`evals/search/__init__.py`](../evals/search/__init__.py)
  Package entrypoint and the quickest place to discover the canonical run command.
- [`evals/search/datasets/`](../evals/search/datasets)
  Search eval case modules plus the dataset assembly point.
- [`evals/search/harness.py`](../evals/search/harness.py)
  Runs the real search agent with injected toolset services and capture support.
- [`evals/search/fixtures.py`](../evals/search/fixtures.py)
  Seeded retrieval results for bundle-stage eval cases.
- [`evals/search/evaluators.py`](../evals/search/evaluators.py)
  Deterministic conversation-contract evaluators such as forbidden response terms and
  no-bundle requirements.
- [`evals/search/run.py`](../evals/search/run.py)
  CLI runner for live eval execution.
- [`evals/search/capture.py`](../evals/search/capture.py)
  Live capture CLI for authoring or refreshing second-step fixtures and transcript samples.
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
`run_search_graph` without needing external search services, embeddings, or Postgres.

For bundle-stage cases, that stub reads seeded results from
[`evals/search/fixtures.py`](../evals/search/fixtures.py) so the live model can decide
whether and how to call `propose_bundle`.

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

This means the judges can see:

- the user message
- the expected search or bundle attributes
- the actual captured tool-call payloads for the specific tool being judged
- the final assistant text for context

The dataset also adds deterministic evaluators for:

- forbidding `bundle` in user-visible assistant prose
- requiring or forbidding `propose_bundle` in selected cases

## Stubbed Runtime Model

The eval harness uses a minimal runtime stub plus injected toolset services.

Important details:

- search execution is replaced at the toolset seam, not by patching imports
- persistence repositories are disabled for the eval run
- attachment storage uses a temp directory per case
- bundle-stage fixtures seed both search results and a matching catalog view so `propose_bundle`
  can hydrate realistic line items without reaching the real catalog
- the real runtime now rejects ungrounded `propose_bundle` items, so fixtures must provide the
  complementary products they expect the model to surface

This keeps the eval focused on query planning while preserving the actual agent and toolset flow.

## Running The Eval

Prerequisites:

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- network access to the configured model backend

Run:

```bash
uv run python -m evals.search
```

Verbose mode:

```bash
uv run python -m evals.search --verbose
```

Optional concurrency override:

```bash
uv run python -m evals.search --max-concurrency 2
```

The runner will:

- set `ALLOW_MODEL_REQUESTS=1` if it is not already set
- configure logging
- configure native Logfire / PydanticAI instrumentation
- execute the dataset directly
- print the report
- exit non-zero if any assertion fails

## Capturing End-To-End Scenarios For Fixture Work

Task `tal_maria_ikea-1iw.9` asked for a reproducible way to capture full end-to-end runs
from the existing search scenarios so second-step evals can be authored from them.

Use the dedicated capture CLI:

```bash
uv run python -m evals.search.capture --output-dir tmp/search-eval-captures
```

To capture only one case:

```bash
uv run python -m evals.search.capture \
  --case rental_gallery_wall \
  --output-dir tmp/search-eval-captures
```

Each capture file includes:

- the case input
- final assistant output
- transcript tool calls
- transcript tool returns
- bundle proposals emitted into shared state

This capture path is intended for fixture authoring and debugging. The authoritative
eval grading still uses native span extraction during `evals.search.run`.

For the hallway-lighting follow-up work, keep thread `agent_search-286fe4b8` in the
fixture notes and use Logfire only as a supplemental grounding source when the historical
trace is available. The later Mark 17 investigation could only recover a follow-up UI lookup
where `GET /api/threads/agent_search-286fe4b8` returned `404`, so the fixture-backed cases are
the durable guardrail for the original failure shape.

## Why This Lives Outside Pytest

Prompt and model evals are not the same thing as deterministic unit tests.
They have different ergonomics, different failure modes, and different runtime needs.

This repo now treats them separately:

- `tests/` is for deterministic pytest coverage
- `evals/` is for direct, live, model-facing evaluation harnesses

Deterministic tests still exist for the shared helpers and toolset seams, but the eval itself
is not a pytest test.

## Extending The Dataset

Add new cases in a focused module under [`evals/search/datasets/`](../evals/search/datasets).
Keep the assembly in [`evals/search/datasets/__init__.py`](../evals/search/datasets/__init__.py)
small, and put shared authoring helpers in
[`evals/search/datasets/common.py`](../evals/search/datasets/common.py).

Keep `expected_search_attributes` and `expected_bundle_attributes` focused on:

- concrete must-have constraints
- required product categories or adjuncts
- meaningful exclusions
- one or two creative reasoning expectations

Avoid turning the rubric into an exact string template.
The judge should grade whether the query set solves the request well, not whether it matches a single phrasing.
