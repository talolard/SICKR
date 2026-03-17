# Search Agent Eval: Tool-Call Quality

This document describes the evaluation harness for the search agent's
**query decomposition** — the reasoning step where the agent translates a
natural-language user request into structured `run_search_graph` tool calls
(semantic queries + filters).

---

## Table of Contents

- [Search Agent Eval: Tool-Call Quality](#search-agent-eval-tool-call-quality)
  - [Table of Contents](#table-of-contents)
  - [What we're evaluating (and what we're not)](#what-were-evaluating-and-what-were-not)
    - [Why isolate tool calls?](#why-isolate-tool-calls)
  - [Architecture overview](#architecture-overview)
  - [Data flow diagram](#data-flow-diagram)
  - [File inventory](#file-inventory)
  - [The pydantic\_evals framework](#the-pydantic_evals-framework)
    - [Why expected\_attributes live in EvalInput, not expected\_output](#why-expected_attributes-live-in-evalinput-not-expected_output)
  - [The task function: `run_search_agent`](#the-task-function-run_search_agent)
  - [Why we stub the search pipeline](#why-we-stub-the-search-pipeline)
  - [Why we monkeypatch the toolset module](#why-we-monkeypatch-the-toolset-module)
  - [Why `MagicMock(spec=...)` for the runtime](#why-magicmockspec-for-the-runtime)
  - [Why `max_concurrency=1`](#why-max_concurrency1)
  - [The eval cases](#the-eval-cases)
    - [1. `pet_safe_dark_hallway` — Constraint exclusion + creative search](#1-pet_safe_dark_hallway--constraint-exclusion--creative-search)
    - [2. `toddler_room_tight_gap` — Hard dimension filters + add-on bundling](#2-toddler_room_tight_gap--hard-dimension-filters--add-on-bundling)
    - [3. `balcony_wfh_setup` — Material constraints + multi-product bundle](#3-balcony_wfh_setup--material-constraints--multi-product-bundle)
    - [4. `reading_nook_under_stairs` — Unusual shapes + creative categories](#4-reading_nook_under_stairs--unusual-shapes--creative-categories)
    - [5. `rental_gallery_wall` — Negative constraints + adhesive semantics](#5-rental_gallery_wall--negative-constraints--adhesive-semantics)
  - [The LLM judge](#the-llm-judge)
    - [The rubric](#the-rubric)
  - [Running the evals](#running-the-evals)
    - [Prerequisites](#prerequisites)
    - [Quick run (summary table only)](#quick-run-summary-table-only)
    - [Verbose run (inputs + outputs + judge reasons)](#verbose-run-inputs--outputs--judge-reasons)
    - [Timing](#timing)
  - [Interpreting results](#interpreting-results)
    - [Non-determinism](#non-determinism)
  - [Extending the dataset](#extending-the-dataset)
    - [Tips for writing good expected\_attributes](#tips-for-writing-good-expected_attributes)

---

## What we're evaluating (and what we're not)

**In scope**: given a user message like _"My hallway is echoey and dark, I have
dogs, budget €200"_, does the search agent produce a good _set_ of
`SearchQueryInput` objects?  Do they:

- Cover the anchor product, essential add-ons, and creative alternatives?
- Use structured filters correctly (dimensions, price, exclude_keyword)?
- Demonstrate lateral/creative semantic queries beyond literal keywords?

**Out of scope**: we do NOT test whether the retrieval pipeline returns good
results for those queries.  Embedding quality, reranking, diversification, and
Milvus indexing are separate concerns.  This eval is purely about the agent's
_reasoning about what to search for_.

### Why isolate tool calls?

The search agent's core value proposition is query decomposition.  A user says
something fuzzy ("quiet down my hallway, I have cats") and the agent must
infer: wall panels for acoustics, artificial plants for darkness, wall-mounted
rails for pet safety, and price caps within budget.  This reasoning step is:

- The **most sensitive to prompt changes** — a single wording tweak can add or
  drop entire query categories.
- The **cheapest to evaluate** — no need for a running vector DB, embedder, or
  reranker.  We just need the model to generate tool calls.
- The **hardest to assert deterministically** — there are many valid ways to
  express "exclude floor products" (via `exclude_keyword: "floor"`, via
  semantic phrasing like "wall-mounted only", via both).  Deterministic string
  matching would be brittle and miss valid alternatives.

This is why we use an LLM judge rather than exact assertions.

---

## Architecture overview

The eval has three moving parts:

| Component | Role |
|-----------|------|
| **Task function** (`run_search_agent`) | Runs the real search agent against a user message, stubs the pipeline, captures tool calls |
| **Dataset** (`CASES`) | 5 eval cases, each with a user message and a list of `expected_attributes` |
| **Evaluator** (`LLMJudge`) | An LLM (gemini-2.5-flash) that reads the tool calls and grades them against the expected attributes |

The key insight: we run the _real_ search agent with real Gemini API calls, so
the agent uses the actual prompt and model.  But we intercept the search
pipeline before it hits any infrastructure, so we never need Milvus, embeddings,
or DuckDB.  The agent sees empty results and responds accordingly — we don't
care about its text response, only about _which queries it decided to make_.

---

## Data flow diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      pydantic_evals.Dataset                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐       ┌─────────────┐         │
│  │  Case 1     │  │  Case 2     │  ...  │  Case 5     │         │
│  │  EvalInput  │  │  EvalInput  │       │  EvalInput  │         │
│  └──────┬──────┘  └──────┬──────┘       └──────┬──────┘         │
│         │                │                     │                │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
   ┌─────────────────────────────────────────────────┐
   │            run_search_agent(inputs)              │
   │                                                  │
   │  1. build_search_agent()                         │
   │     └─ real Gemini model + real prompt.md        │
   │                                                  │
   │  2. _build_stub_deps()                           │
   │     └─ MagicMock runtime (no DB/Milvus)          │
   │     └─ temp-dir AttachmentStore                  │
   │     └─ empty SearchAgentState                    │
   │                                                  │
   │  3. Monkeypatch pipeline ──────────────────┐     │
   │                                            │     │
   │  4. agent.run(user_message, deps) ◄────────┤     │
   │     │                                      │     │
   │     │  Agent calls run_search_graph tool    │     │
   │     │  └─ toolset calls pipeline_batch ─────┘     │
   │     │     └─ STUB captures SearchQueryInput       │
   │     │     └─ returns empty results                │
   │     │                                             │
   │     │  Agent may call propose_bundle tool         │
   │     │  └─ hits mock catalog → ValueError          │
   │     │  └─ agent retries or skips                  │
   │                                                   │
   │  5. Collect tool calls from:                      │
   │     a. captured_queries (typed, preferred)        │
   │     b. message history ToolCallParts (fallback)   │
   │                                                   │
   │  6. Return EvalOutput                             │
   │     └─ tool_calls_json: serialised queries        │
   │     └─ agent_response: final text                 │
   └──────────────────────┬────────────────────────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────┐
   │              LLMJudge (gemini-2.5-flash)         │
   │                                                  │
   │  Receives:                                       │
   │    <Input>                                       │
   │      user_message: "My hallway is echoey..."     │
   │      expected_attributes:                        │
   │        - "sound-dampening wall solutions"        │
   │        - "artificial OR low-light plants"        │
   │        - "floor products excluded"               │
   │        - ...                                     │
   │    </Input>                                      │
   │    <Output>                                      │
   │      tool_calls_json: [                          │
   │        {query_id: "q1", semantic_query: "...",   │
   │         filters: {exclude_keyword: "floor", ...}}│
   │        ...                                       │
   │      ]                                           │
   │      agent_response: "No matches found..."       │
   │    </Output>                                     │
   │                                                  │
   │  Grades against rubric → PASS / FAIL + reason    │
   └──────────────────────┬────────────────────────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────┐
   │              Evaluation Report                    │
   │                                                  │
   │  ┌──────────────────────┬────────────┬────────┐  │
   │  │ Case                 │ Assertions │ Time   │  │
   │  ├──────────────────────┼────────────┼────────┤  │
   │  │ pet_safe_dark_hallway│ ✔          │ 38.5s  │  │
   │  │ toddler_room_tight   │ ✗          │ 39.4s  │  │
   │  │ balcony_wfh_setup    │ ✔          │ 42.0s  │  │
   │  │ reading_nook          │ ✗          │ 34.9s  │  │
   │  │ rental_gallery_wall  │ ✔          │ 21.2s  │  │
   │  ├──────────────────────┼────────────┼────────┤  │
   │  │ Average              │ 60% ✔      │ 35.2s  │  │
   │  └──────────────────────┴────────────┴────────┘  │
   └──────────────────────────────────────────────────┘
```

---

## File inventory

| File | Purpose |
|------|---------|
| [`tests/chat/agents/search/eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py) | Dataset definition, task function, evaluator config, and a `main()` for verbose output |
| [`tests/chat/agents/search/run_eval.py`](../tests/chat/agents/search/run_eval.py) | Thin runner that prints only the summary table (for quick prompt iteration) |
| [`src/ikea_agent/chat/agents/search/prompt.md`](../src/ikea_agent/chat/agents/search/prompt.md) | The search agent's system prompt (the thing we're evaluating) |
| [`src/ikea_agent/chat/agents/search/agent.py`](../src/ikea_agent/chat/agents/search/agent.py) | Agent builder — `build_search_agent()` wires model + prompt + toolset |
| [`src/ikea_agent/chat/agents/search/toolset.py`](../src/ikea_agent/chat/agents/search/toolset.py) | Tool definitions (`run_search_graph`, `propose_bundle`, etc.) |
| [`src/ikea_agent/shared/types.py`](../src/ikea_agent/shared/types.py) | `SearchQueryInput`, `RetrievalFilters`, `SearchBatchToolResult`, etc. |

---

## The pydantic_evals framework

`pydantic_evals` provides a `Dataset[InputT, OutputT]` that:

1. Holds a list of `Case` objects, each with typed `inputs` and optional
   `expected_output`.
2. Accepts a **task function** `async (InputT) -> OutputT` that is called once
   per case.
3. Runs **evaluators** on each `(inputs, output)` pair.
4. Produces a report with pass/fail per case, timing, and reasons.

In our setup:

- `InputT = EvalInput` — the user message + expected attributes.
- `OutputT = EvalOutput` — the captured tool calls (JSON) + agent response text.
- The task function is `run_search_agent`.
- The evaluator is `LLMJudge`.

### Why expected_attributes live in EvalInput, not expected_output

`LLMJudge` has an `include_input` flag that sends the full `EvalInput` to the
judge prompt.  By packing `expected_attributes` into the input, the judge
sees both the user message and the checklist in its `<Input>` block.  We don't
use `expected_output` because there's no single "correct" output — the
attributes are a rubric, not a template.

---

## The task function: `run_search_agent`

This is the function `Dataset.evaluate()` calls for each case.  It:

1. **Builds a fresh agent** via `build_search_agent()`.  This uses the _real_
   prompt from `prompt.md` and a _real_ Gemini model (the same one production
   uses).  A fresh agent per case ensures prompt edits take effect without
   restart.

2. **Creates stub deps** via `_build_stub_deps()`.  The agent's tools need a
   `SearchAgentDeps` object containing a `ChatRuntime`, `AttachmentStore`, and
   `SearchAgentState`.  The stub provides mock versions of these — no real
   database, Milvus, or embedder is needed.

3. **Monkeypatches the pipeline** — replaces `run_search_pipeline_batch` in the
   toolset module's namespace with a stub that captures the `SearchQueryInput`
   list and returns empty results.

4. **Runs the agent** — `agent.run(user_message, deps=deps)`.  The model
   generates tool calls, the toolset function processes them through the
   (stubbed) pipeline, and the agent gets back empty results.

5. **Collects tool calls** from two sources:
   - **`captured_queries`**: typed `SearchQueryInput` dataclasses captured by
     the stub.  These are the "ground truth" — they've been through the
     toolset's normalization (e.g. `candidate_pool_limit` clamping).
   - **Message history `ToolCallPart`s**: raw JSON args from the agent's
     messages.  This is the fallback if the stub wasn't reached (e.g. the
     agent didn't call `run_search_graph` at all).

6. **Returns `EvalOutput`** with the serialised queries and the agent's text
   response.

---

## Why we stub the search pipeline

The `run_search_graph` tool in the toolset calls `run_search_pipeline_batch`,
which is the heavy function that:

- Embeds the semantic query via the Gemini embedder
- Searches the Milvus vector index
- Applies keyword/dimension/price filters in DuckDB
- Reranks results
- Applies diversification

All of that requires a live `ChatRuntime` with real services.  But we don't
care what results come back — we only care about what queries the agent
_decided to send_.  The stub:

- **Captures** the `SearchQueryInput` objects (our grading surface).
- **Returns empty results** (`returned_count=0` for every query).
- Is **fast** — no network calls, no disk I/O.

The agent sees empty results and typically responds with "I couldn't find
exact matches, here are some suggestions to broaden your search."  That text
response is included in the eval output but is not the primary grading signal.

---

## Why we monkeypatch the toolset module

The toolset file has this import at the top:

```python
# In src/ikea_agent/chat/agents/search/toolset.py
from ikea_agent.chat.search_pipeline import run_search_pipeline_batch
```

This creates a **direct name binding** in the toolset module's namespace.  When
the tool function calls `run_search_pipeline_batch(...)`, Python resolves that
name in the toolset module's `__dict__`, _not_ in the original
`search_pipeline` module.

If we patched the original module:

```python
# ❌ This would NOT work:
search_pipeline.run_search_pipeline_batch = stub
```

The toolset would still call its own locally-bound reference to the original
function.  So instead we patch the name _where it's used_:

```python
# ✅ This works:
import ikea_agent.chat.agents.search.toolset as _toolset_mod
_toolset_mod.run_search_pipeline_batch = stub
```

We save the original reference and restore it in a `try/finally` to avoid
leaking the stub into other code.

---

## Why `MagicMock(spec=...)` for the runtime

The search agent's toolset calls helper functions that probe the runtime for
optional capabilities:

```python
# In src/ikea_agent/chat/agents/shared.py
def search_repository(runtime: ChatRuntime) -> SearchRepository | None:
    if not hasattr(runtime, "session_factory"):
        return None
    return SearchRepository(runtime.session_factory)
```

A plain `MagicMock()` has _every_ attribute (`hasattr` always returns `True`).
This means `search_repository()` would construct a real `SearchRepository`
backed by a MagicMock session factory.  When that session factory is later
called by SQLAlchemy, it returns another MagicMock, and eventually something
tries to `await` it or do arithmetic with it, causing cryptic errors like:

    TypeError: object MagicMock can't be used in 'await' expression

The fix: `MagicMock(spec=["settings", "catalog_repository"])` restricts the
mock to _only_ those two attributes.  Now `hasattr(runtime, "session_factory")`
returns `False`, and the helper functions return `None` (no repository),
cleanly skipping all persistence code.

The `catalog_repository.read_product_by_key` is configured to return `None` so
that if the agent tries to call `propose_bundle` (which hydrates product
details from the catalog), it gets a `ValueError("Unknown product id")` rather
than crashing deep inside SQLAlchemy.

---

## Why `max_concurrency=1`

The monkeypatch swaps a module-level name:

```python
_toolset_mod.run_search_pipeline_batch = _stub_pipeline
```

If two eval cases ran concurrently:

1. Case A patches the function and starts running
2. Case B patches the function (overwriting A's stub—fine, both use similar stubs)
3. Case A finishes and restores the **original** function
4. Case B is still running but the function is now the original → hits real
   pipeline → crashes

With `max_concurrency=1`, cases run sequentially and the patch/restore cycle is
safe.

An alternative design would inject the pipeline as a dependency through the
agent's deps, making it easy to swap per-run without global patching.  But that
would change production code to accommodate eval ergonomics — not worth the
coupling.  Sequential eval runs are fast enough (~3 min for 5 cases).

---

## The eval cases

Each case is a realistic user query **deliberately different from** the
scenarios in `prompt.md` (so we test generalisation, not memorisation):

### 1. `pet_safe_dark_hallway` — Constraint exclusion + creative search

> "My hallway is really echoey and dark. I have two dogs that chew anything on
> the floor. I want it to feel more alive — maybe greenery? Budget around €200
> total."

**Expected attributes**:

- Sound-dampening wall solutions
- Artificial / low-light plants (not real plants)
- Floor-level products excluded
- Mounting system for wall display
- Price filters within €200

**What it tests**: can the agent infer implicit constraints (dogs → no floor
items), handle the darkness constraint (artificial plants), and apply budget
filters?

### 2. `toddler_room_tight_gap` — Hard dimension filters + add-on bundling

> "We have a 75cm niche in the toddler's room. We need somewhere to store
> clothes and change diapers. Max height 100cm because there's a window above.
> Under €250."

**Expected attributes**:

- Width ≤ 75cm and height ≤ 100cm in dimension filters
- Changing pad/mat query
- Organisational add-ons (dividers, bins)
- Creative cross-category query (not just "nursery dresser")
- Price cap ≤ €250

**What it tests**: does the agent use structured dimension filters (not just
semantic phrasing), and does it think beyond the obvious product category?

### 3. `balcony_wfh_setup` — Material constraints + multi-product bundle

> "I want to set up a small outdoor workspace on my balcony. It's about 100cm
> wide. Needs to survive rain when I'm not using it. I'd like to keep it under
> €300."

**Expected attributes**:

- Weather-resistant / outdoor / waterproof material queries
- Width ≤ 100cm dimension filters
- Desk/table + seating + accessories
- Indoor-only terms excluded
- Price within €300

**What it tests**: material-based reasoning, multi-product coordination, and
the agent's ability to exclude irrelevant product domains.

### 4. `reading_nook_under_stairs` — Unusual shapes + creative categories

> "There's an awkward triangular space under my stairs — about 120cm wide at
> the base, slopes down to nothing. I'd love a cozy reading spot there.
> Something warm and inviting. Maybe €150 max."

**Expected attributes**:

- Small/awkward-space seating (floor cushion, bean bag, low bench)
- Reading light
- Soft textiles (throws, cushions)
- Low-profile / compact dimension awareness
- Creative semantic queries (meditation cushion, upholstered floor mat)
- Budget ≤ €150

**What it tests**: can the agent handle spatial constraints that don't map
cleanly to standard dimension filters?  Does it explore non-obvious product
categories?

### 5. `rental_gallery_wall` — Negative constraints + adhesive semantics

> "I rent my apartment and can't drill holes. I want to create a gallery wall
> in my living room — mix of photos, small shelves, and maybe a clock. About
> 200cm wide wall. Under €180."

**Expected attributes**:

- No-drill / adhesive / damage-free mounting
- Drill/screw terms excluded
- Photo frames, shelves, decorative accents
- Creative semantics (adhesive gallery kit, command strip shelf)
- Price within €180

**What it tests**: negative constraints ("can't drill") should appear as both
semantic query phrasing and explicit `exclude_keyword` filters.  Multiple
product categories must coexist in one solution.

---

## The LLM judge

We use `pydantic_evals.evaluators.LLMJudge` with these settings:

| Setting | Value | Why |
|---------|-------|-----|
| `model` | `google-gla:gemini-2.5-flash` | Cheaper / faster than the agent's model; flash is good enough for rubric grading |
| `include_input` | `True` | The judge needs to see `expected_attributes` to know what to check |
| `include_expected_output` | `False` | We don't define a single correct output — the attributes are the rubric |
| `rubric` | See below | Tells the judge the grading criteria |

### The rubric

The judge receives something like:

```
<Input>
EvalInput(user_message="My hallway is really echoey...",
          expected_attributes=["sound-dampening wall solutions", ...])
</Input>
<Output>
EvalOutput(tool_calls_json='[{"query_id": "q1", ...}]',
           agent_response="Unfortunately no matches...")
</Output>
```

And grades against this rubric:

> **PASS** if:
>
> 1. Every expected attribute is addressed by at least one query
> 2. Queries form a coherent solution bundle (not just one search)
> 3. Filters use correct field names and reasonable values
> 4. At least one creative/lateral semantic query exists
>
> **FAIL** if any expected attribute is unaddressed, queries are trivially
> repetitive, or hard constraints (dimensions, budget) are ignored.

The judge returns `{pass: bool, reason: str}`.  The reason is visible in
verbose output mode.

---

## Running the evals

### Prerequisites

- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) set in your environment
- That's it — no Milvus, no DuckDB, no running server

### Quick run (summary table only)

```bash
uv run python tests/chat/agents/search/run_eval.py
```

Output:

```
Evaluation Summary: search_agent_tool_call_quality
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Case ID                   ┃ Assertions ┃ Duration ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ pet_safe_dark_hallway     │ ✔          │    38.5s │
│ toddler_room_tight_gap    │ ✗          │    39.4s │
│ balcony_wfh_setup         │ ✔          │    42.0s │
│ reading_nook_under_stairs │ ✗          │    34.9s │
│ rental_gallery_wall       │ ✔          │    21.2s │
│ Averages                  │ 60.0% ✔    │    35.2s │
└───────────────────────────┴────────────┴──────────┘
```

### Verbose run (inputs + outputs + judge reasons)

```bash
ALLOW_MODEL_REQUESTS=1 uv run python -m tests.chat.agents.search.eval_search_tool_calls
```

### Timing

- Each case: ~30-40s (one Gemini call for the agent + one for the judge)
- 5 cases sequential: ~3 minutes total
- Runs are sequential (`max_concurrency=1`) due to the monkeypatch constraint

---

## Interpreting results

- **✔ (PASS)**: the agent's queries covered all expected attributes, used
  filters correctly, and included creative searches.
- **✗ (FAIL)**: the judge found at least one expected attribute unaddressed.
  Run in verbose mode to see the judge's reason — it will say exactly which
  attribute(s) were missing.
- **Error rows**: the task function itself crashed (e.g. a mock wasn't set up
  correctly).  Check the error message in the "Case Failures" table.

### Non-determinism

Because the agent uses a real LLM (Gemini with thinking enabled), results are
**non-deterministic**.  A case that passes one run may fail the next.  This is
expected.  Track pass rates over multiple runs to get a stable signal.  If a
case is flaky, the prompt likely covers it _marginally_ — a good signal that
the reasoning for that scenario should be strengthened in `prompt.md`.

---

## Extending the dataset

To add a new case:

1. Write a realistic user message that exercises a pattern you want to test.
2. Write 4-7 `expected_attributes` — concrete, checkable claims about what the
   tool calls should contain.  Be specific enough that a judge can verify them
   from JSON, but flexible enough to allow multiple valid phrasings.
3. Add a `Case(name="...", inputs=EvalInput(...))` to the `CASES` list in
   `eval_search_tool_calls.py`.
4. Run the eval.  If the case fails, check whether it's a prompt gap (fix the
   prompt) or an overly strict attribute (loosen the check).

### Tips for writing good expected_attributes

- **Be specific about the filter type**: "Width ≤ 75cm applied via dimension
  filters" is better than "queries respect width constraint" (the judge can
  check for `max_cm: 75` in the JSON).
- **Allow alternatives**: "artificial OR low-light plants" lets the agent
  satisfy the attribute either way.
- **Name the creative leap**: "e.g. 'meditation cushion', 'kids lounge seat'"
  gives the judge calibration for what counts as creative.
- **Don't over-constrain**: avoid requiring specific `query_id` names or exact
  `semantic_query` strings — that would test memorisation, not reasoning.
