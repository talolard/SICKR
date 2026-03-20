# Search Agent Eval Review

This review covers [`docs/search_agent_eval.md`](./search_agent_eval.md) and the code it pointed at when the review was written.
It is intentionally preserved as a critique of the **pre-migration** harness that used to live under `tests/chat/agents/search/`.
That harness has now been replaced by the authoritative `evals/search/` implementation, and the old `tests/...` eval files referenced below have been deleted.

The historical files reviewed were:

- [`tests/chat/agents/search/eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py)
- [`tests/chat/agents/search/run_eval.py`](../tests/chat/agents/search/run_eval.py)
- [`tests/chat/agents/search/eval_dataset.py`](../tests/chat/agents/search/eval_dataset.py)
- [`tests/chat/agents/search/test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py)
- [`src/ikea_agent/chat/agents/search/toolset.py`](../src/ikea_agent/chat/agents/search/toolset.py)
- [`src/ikea_agent/chat/agents/shared.py`](../src/ikea_agent/chat/agents/shared.py)

External guidance reviewed:

- [PydanticAI evals quick start](https://ai.pydantic.dev/evals/quick-start/)
- [PydanticAI LLMJudge docs](https://ai.pydantic.dev/evals/evaluators/llm-judge/)
- [PydanticAI span-based evaluations](https://ai.pydantic.dev/evals/integrations/span-based/)
- [PydanticAI Logfire instrumentation docs](https://ai.pydantic.dev/logfire/)
- [PydanticAI testing docs: `capture_run_messages()`](https://ai.pydantic.dev/testing/)
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices/)
- [OpenAI realtime eval guide](https://developers.openai.com/cookbook/examples/realtime_eval_guide/)

## Bottom line

The core idea is excellent: evaluating only the search-agent tool call is the right level of abstraction for this problem. It isolates the model behavior you actually care about, avoids paying retrieval-infra costs, and fits both the Pydantic eval model and general eval-engineering guidance very well.

The implementation around that idea is much rougher than it should be. My honest read is: **smart target, messy harness**. The monkeypatching is not the main sin by itself; the bigger issue is that the repo now has multiple partially-overlapping harnesses, weak dependency seams, and test doubles that only work because other parts of the system happen not to touch them.

## What is working well

- **The behavior under test is well chosen.** [`docs/search_agent_eval.md`](./search_agent_eval.md#what-were-evaluating-and-what-were-not) is correct to isolate query decomposition rather than retrieval quality. That is exactly the kind of scoped eval OpenAI recommends: test the specific model capability, not the whole stack.
- **Using `Dataset` + task function + `LLMJudge` is idiomatic.** Both [`tests/chat/agents/search/eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py) and the newer [`tests/chat/agents/search/eval_dataset.py`](../tests/chat/agents/search/eval_dataset.py) match the intended `pydantic_evals` shape well.
- **`expected_attributes` in the input is a good design choice.** That is a clean way to let the judge see the checklist without pretending there is one canonical tool-call payload.
- **The cases are high-signal.** The scenario writing is much better than average eval writing. They are concrete, varied, and they push the prompt into real decomposition work rather than synthetic toy prompts.
- **The old harness captures normalized tool inputs, not just transcript text.** In [`eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py#L232), preferring captured `SearchQueryInput` objects over raw message args is the right instinct. That is closer to the actual contract than free-form text inspection.

## What is hackish or over-engineered

### 1. The docs describe one harness, but the repo now has two

This is the biggest maintainability problem.

- [`docs/search_agent_eval.md`](./search_agent_eval.md#file-inventory) documents only the older script-centric flow.
- [`tests/chat/agents/search/run_eval.py`](../tests/chat/agents/search/run_eval.py) still imports the old harness.
- The repo also has a newer pytest split across [`eval_dataset.py`](../tests/chat/agents/search/eval_dataset.py) and [`test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py).

That is not just “a little drift”. It means there is no single authoritative implementation. When a system needs a design doc plus two different runnable harnesses for five eval cases, that is overbuilt in the wrong place.

My take: pick one harness and delete the other. Right now the repo is paying complexity tax for both.

### 1a. What I mean by the "old harness"

The repo currently has two distinct implementations of the same eval idea.

The **old harness** is the script-centric path:

- [`docs/search_agent_eval.md`](./search_agent_eval.md)
- [`tests/chat/agents/search/eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py)
- [`tests/chat/agents/search/run_eval.py`](../tests/chat/agents/search/run_eval.py)

Characteristics:

- one file owns the dataset, task function, stubs, judge, and `main()`
- docs and runner both point at it
- it captures normalized `SearchQueryInput` objects from the patched pipeline
- it runs sequentially, which is consistent with the monkeypatch constraint

The **newer harness** is the pytest-oriented split:

- [`tests/chat/agents/search/eval_dataset.py`](../tests/chat/agents/search/eval_dataset.py)
- [`tests/chat/agents/search/test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py)

Characteristics:

- separates dataset definition from execution
- fits pytest better
- is less faithful to the stated eval target in a few important ways
- currently contains the weaker runtime stub and the unsafe `max_concurrency=2`

So "old" here does **not** mean "obviously obsolete". It means "the earlier script-based implementation that the docs still describe".

### 2. The monkeypatch is understandable, but it became an architectural center of gravity

The explanation in [`docs/search_agent_eval.md`](./search_agent_eval.md#why-we-monkeypatch-the-toolset-module) is technically correct. Patching the name where it is used is the right patch target.

But the amount of machinery orbiting that patch is a smell:

- special runtime doubles
- sequential-only execution rules
- bespoke runner behavior
- fallback extraction logic
- long prose justifying Python name binding details

That usually means the missing abstraction is not “more documentation”; it is “a real injection seam”.

I do **not** think “there is a monkeypatch” automatically means “bad test”. For a narrow seam, monkeypatching can be pragmatic. What makes this hackish is that the patch is compensating for production code that gives the eval no first-class way to substitute the search executor.

The clean design would be one of:

- `build_search_toolset(search_runner=...)`
- `SearchAgentDeps(search_runner=...)`
- native PydanticAI span capture via Logfire/OpenTelemetry, without patching the toolset global

Pydantic’s span-based eval docs are especially relevant here: tool calls are observable events. In this repo, the right answer is to use **native PydanticAI instrumentation via Logfire**, not to build a custom span layer.

That matches current repo policy and current runtime setup:

- [`docs/logging.md`](../docs/logging.md) already says to prefer native instrumentation first
- [`src/ikea_agent/observability/logfire_setup.py`](../src/ikea_agent/observability/logfire_setup.py#L23) already calls `logfire.instrument_pydantic_ai()`

So the critique here is narrower than "you should capture traces somehow". It is: if we want trace-based evals, we should use the tracing stack we already have rather than inventing a parallel mechanism.

The concrete reference here is PydanticAI’s testing API, especially `capture_run_messages()`. The pattern is roughly:

```python
import json

from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ModelResponse, ToolCallPart

with capture_run_messages() as messages:
    result = await agent.run(user_message, deps=deps)

tool_calls: list[dict[str, object]] = []
for msg in messages:
    if not isinstance(msg, ModelResponse):
        continue
    for part in msg.parts:
        if isinstance(part, ToolCallPart) and part.tool_name == "run_search_graph":
            args = part.args if isinstance(part.args, dict) else json.loads(part.args or "{}")
            tool_calls.append(args)
```

That does **not** require Logfire. It captures the model-emitted tool args from the run transcript. The tradeoff is that this gives you the pre-tool-call payload, not necessarily the fully normalized "executed" query objects. If you care about executed normalized inputs, dependency injection at the toolset seam is still the better answer.

For eval architecture, this suggests a clear preference order:

1. **Best trace-level hook:** native PydanticAI spans via Logfire/OpenTelemetry
2. **Best direct-agent hook:** inject toolset services and capture normalized executed inputs inside the tool layer
3. **Fallback direct-run hook:** inspect `ToolCallPart`s from `capture_run_messages()` / `all_messages()`

I would prefer options 1 or 2 over inventing any repo-local span capture mechanism.

### 3. The newer pytest harness reintroduces the exact concurrency bug the docs warn about

The doc is explicit that the global patch requires sequential execution:

- [`docs/search_agent_eval.md`](./search_agent_eval.md#why-max_concurrency1)
- [`eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py#L54)

But the newer test runs:

```python
report = await dataset.evaluate(
    _search_agent_task,
    name="search_tool_call_quality",
    max_concurrency=2,
)
```

See [`tests/chat/agents/search/test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py#L196).

That is not just inelegant. It is a real correctness bug. The test is doing the thing the doc says is unsafe.

This is exactly the sort of failure mode eval harnesses should avoid: the harness itself introduces nondeterminism that has nothing to do with model quality.

### 4. The newer runtime stub is weaker than the old `MagicMock(spec=...)` hack

This part is surprising: the old hack is actually better.

The doc explains why [`eval_search_tool_calls.py`](../tests/chat/agents/search/eval_search_tool_calls.py#L207) uses `MagicMock(spec=["settings", "catalog_repository"])`: it deliberately avoids exposing `session_factory`, because [`search_repository()`](../src/ikea_agent/chat/agents/shared.py#L38) only checks `hasattr(runtime, "session_factory")`.

The newer `_RuntimeStub` in [`test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py#L58) sets:

```python
session_factory: object = None
```

Given [`search_repository()`](../src/ikea_agent/chat/agents/shared.py#L38), that means the runtime now **does** look persistence-capable, and `run_search_graph()` will instantiate `SearchRepository(None)` and eventually blow up when it tries to call the session factory.

I verified this locally by patching the pipeline and calling `run_search_graph()` with `_RuntimeStub`; it raises:

```text
TypeError: 'NoneType' object is not callable
```

That is a strong signal that the seam is bad. The old version was hacky, but at least it was intentionally hacky. The new version is cleaner-looking while being less sound.

### 5. The newer harness is less faithful to the stated eval target

The doc’s stated target is “tool-call quality”. The old harness returns empty results and prefers captured normalized queries. That keeps the grading surface close to the actual decision you care about.

The newer harness regresses on both fronts:

- [`_PipelineCapture`](../tests/chat/agents/search/test_search_evals.py#L71) returns fake product results instead of empty results.
- [`_extract_tool_calls()`](../tests/chat/agents/search/test_search_evals.py#L125) captures all `ToolCallPart`s from transcript history, not just `run_search_graph`.

Why this matters:

- returning stub results can change downstream agent behavior, so the eval is no longer “only query decomposition”
- raw transcript args are a weaker contract than normalized tool inputs
- including unrelated tools adds noise to the judge input

This is a good example of a harness getting more bespoke while becoming less precise.

### 6. There is too much bespoke glue for a small dataset

Individually, none of these helpers are terrible:

- [`_make_empty_batch_result()`](../tests/chat/agents/search/eval_search_tool_calls.py#L176)
- [`_extract_tool_calls()`](../tests/chat/agents/search/test_search_evals.py#L125)
- [`run_eval.py`](../tests/chat/agents/search/run_eval.py)
- the manual “scan scores and `pytest.fail`” loop in [`test_search_evals.py`](../tests/chat/agents/search/test_search_evals.py#L203)

Collectively, they are too much custom scaffolding for five cases. This is the kind of code that tends to rot because none of it is central product logic, but all of it can break the eval story.

The biggest red flag is not that any one helper exists. It is that the helpers exist in two different versions.

## Where the design aligns with Pydantic eval docs and general best practices

- **Scoped task function:** very aligned. `pydantic_evals` wants a concrete task function over typed inputs and outputs. The project is doing that.
- **Pytest integration:** the newer pytest harness is aligned with Pydantic’s recommended testing style.
- **LLM judge for rubric-based comparison:** aligned. OpenAI’s eval guidance explicitly notes that LLMs are better at discriminating between options and scoring against specific criteria than producing open-ended gold outputs.
- **Task-specific cases:** aligned. These are not generic “does the model seem good?” vibe checks.

## Where it diverges from best practices

### 1. Weak determinism at the harness boundary

OpenAI’s eval guidance emphasizes scoped tests, automation, and stable mocks. The current harness still has avoidable instability:

- live agent model
- live judge model
- global monkeypatch
- duplicate runners

Some nondeterminism is unavoidable because this is an LLM eval. The global patch race is not.

### 2. Diagnostics are too monolithic

Both harnesses mostly boil tool-call quality down to one broad LLM rubric. That is workable for early iteration, but it is not ideal for debugging.

Pydantic’s evaluator model supports multiple evaluators. This harness would be easier to interpret if it split the rubric into a few labeled checks, for example:

- hard constraints captured
- query coverage / solution completeness
- creativity / lateral search
- tool schema correctness

Right now, when the judge says “fail”, the diagnosis is still fairly prose-heavy.

### 3. Pre-production context matters

For this repository’s current stage, I would **not** criticize the eval for being hand-authored, exploratory, or lightly governed. This is pre-production prompt and tool-shape work, so a small hand-written dataset and an uncalibrated LLM judge are reasonable for now.

The problem is not “this isn’t production-grade eval ops yet”. The problem is narrower and more actionable:

- duplicate harnesses
- weak injection seams
- concurrency-unsound patching
- stubs that do not model capabilities cleanly

## Specific praise that should stay

- Keep the **tool-call-only** framing. That is the smartest part of the whole design.
- Keep the **real prompt + real model** in the loop for this eval. It is appropriate because the prompt is what you are trying to tune.
- Keep the **attribute-based judging** instead of pretending there is one canonical JSON payload.
- Keep the **creative scenario writing**. The cases are noticeably thoughtful.
- Keep the **lightweight exploratory scope**. For pre-production work, this level of eval maturity is acceptable.

## Target repo shape for evals

I agree with moving these out of `tests/`. Evals and tests are related, but they are not the same thing:

- `tests/` should answer "does the code behave correctly and deterministically?"
- `evals/` should answer "does the model+prompt system perform well against a rubric or dataset?"

Keeping them together encourages exactly the current confusion: pytest wrappers, eval runners, and one-off harness utilities end up mixed into the test tree even though they have different failure modes and different maintenance needs.

The target should be a single authoritative eval home under `evals/`, with the current search eval consolidated there and the duplicate test-era harness deleted after the replacement is in place.

### Suggested structure

```text
evals/
  base/
    __init__.py
    dataset.py
    harness.py
    capture.py
    services.py
    types.py
  search/
    __init__.py
    dataset.py
    harness.py
    run.py
    review_notes.md
```

### What should live in `evals/base/`

- `types.py`
  Shared typed contracts for eval inputs, outputs, capture records, and harness configuration.
- `capture.py`
  Small helpers for extracting grading payloads from Logfire/span traces, AG-UI event traces, or `ToolCallPart` message history.
- `services.py`
  Reusable service dataclasses for toolset dependency injection.
- `harness.py`
  Lightweight reusable base classes or protocols for "build agent", "build deps", "run case", and "extract grading payload".
- `dataset.py`
  Shared helpers for building `Dataset` / `Case` objects and consistent evaluator labels.

That gives you one place for the boring plumbing and keeps per-agent eval code focused on the scenario set and the grading surface.

### Capture sources should be standardized

The shared eval layer should explicitly support two sanctioned capture sources:

- **Logfire/span capture**
  For evals that want trace-level assertions using native PydanticAI instrumentation.
- **AG-UI trace capture**
  For evals that want to judge the UI/server contract as CopilotKit sees it.
- **Direct message capture**
  For evals that run the agent directly and only need model-emitted tool args.

That distinction should be explicit in types and docs. It should not be hidden behind ad hoc per-eval helper functions.

If I had to choose a default direction for new eval infrastructure in this repo, I would choose:

- Logfire/native span capture for trace-aware evals
- AG-UI event trace for UI-contract evals
- direct message capture only as a lightweight fallback

## Builder pattern and DI target

The main cleanup I would recommend documenting is a builder pattern around toolset services, not around the entire agent runtime.

The important idea is:

- production code gets sane defaults
- evals can inject minimal fake services
- tests can inject deterministic stubs
- no module-global patching is needed

### Minimal pattern

```python
from dataclasses import dataclass
from typing import Awaitable, Callable

SearchBatchRunner = Callable[..., Awaitable[SearchBatchToolResult]]

@dataclass(frozen=True, slots=True)
class SearchToolsetServices:
    run_search_batch: SearchBatchRunner
    get_search_repository: Callable[[ChatRuntime], SearchRepository | None]
    get_room_3d_repository: Callable[[ChatRuntime], Room3DRepository | None]

DEFAULT_SEARCH_TOOLSET_SERVICES = SearchToolsetServices(
    run_search_batch=run_search_pipeline_batch,
    get_search_repository=search_repository,
    get_room_3d_repository=room_3d_repository,
)

def build_search_toolset(
    services: SearchToolsetServices = DEFAULT_SEARCH_TOOLSET_SERVICES,
) -> FunctionToolset[SearchAgentDeps]:
    ...
```

That pattern is easy to reuse across toolsets:

- one small `...ToolsetServices` dataclass per agent/toolset
- one `DEFAULT_..._SERVICES`
- one builder function that accepts the services object

This is enough DI to make evals and tests easy, without introducing a large application container.

## Reusable base classes are reasonable here

I do **not** think the repo is being "prompted away" from OOP. The current style guidance favors:

- small functions
- explicit typed data
- few hidden side effects

That tends to push code toward functions + dataclasses rather than inheritance-heavy class trees. That is usually the right default.

But eval harnesses are one of the places where a **small amount** of reusable OOP is justified, because they naturally have stable lifecycle hooks:

- build dataset
- build agent
- build deps
- run one case
- extract the grading payload

That is a reasonable place for a minimal abstract base class or protocol.

### Example sketch

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
DepsT = TypeVar("DepsT")

class AgentEvalHarness(ABC, Generic[InputT, OutputT, DepsT]):
    @abstractmethod
    def build_agent(self): ...

    @abstractmethod
    def build_deps(self) -> DepsT: ...

    @abstractmethod
    async def run_case(self, inputs: InputT) -> OutputT: ...
```

I would keep this kind of base class very small. The purpose is to share harness structure, not to create a framework.

## Discriminated unions and typeguards are a good fit

I agree with your instinct here. A clean way to balance DI and readability is to keep the reusable objects small and typed, and use discriminated unions where capture modes or harness modes differ.

For example, if some evals grade transcript-emitted tool args and others grade normalized executed args, that distinction should be explicit in the type system rather than hidden in helper behavior.

### Example sketch

```python
from dataclasses import dataclass
from typing import Literal, TypeGuard

@dataclass(frozen=True, slots=True)
class TranscriptCapture:
    kind: Literal["transcript"]
    tool_name: str
    args: dict[str, object]

@dataclass(frozen=True, slots=True)
class ExecutedQueryCapture:
    kind: Literal["executed_query"]
    query: SearchQueryInput

CaptureRecord = TranscriptCapture | ExecutedQueryCapture

def is_executed_query_capture(value: CaptureRecord) -> TypeGuard[ExecutedQueryCapture]:
    return value.kind == "executed_query"
```

That is minimal code, but it makes the grading surface explicit and keeps eval logic honest.

## Recommended consolidation direction

If the goal is one eval system under `evals/`, then yes, the repo should aim to delete the duplicate search-eval code under `tests/` after the replacement exists.

The order matters:

1. consolidate the authoritative harness under `evals/search/`
2. move shared helpers into `evals/base/`
3. point docs and runners to that location
4. delete the duplicate `tests/...` search eval harness files

I would treat the current script-era harness as the behaviorally more coherent reference while doing that migration, even though its packaging is worse.

## Specific things I would call debt, not design

- two harnesses for one eval
- a doc that explains old mechanics in great detail but no longer describes the whole system
- capability detection via `hasattr(runtime, "session_factory")`
- a concurrency-unsafe global patch combined with `max_concurrency=2`
- transcript-level capture in the newer harness when the stated target is normalized search queries
- fake retrieval results in a harness whose stated goal is to avoid retrieval behavior entirely

## My blunt assessment

If I were reviewing this in a PR, I would say:

- **The eval target is excellent.**
- **The old harness is hacky but conceptually coherent.**
- **The new harness is cleaner-looking but actually more compromised.**
- **The doc is thoughtful, but it is over-explaining a workaround instead of documenting a stable design.**

So yes: your instinct is right. Testing just the tool call is smart. The current implementation is hackish, and in a few places the newer cleanup attempts made it worse by hiding the hack instead of removing it.

## Important Note

Maintain the evals themelves, e.g. the actual cases.
