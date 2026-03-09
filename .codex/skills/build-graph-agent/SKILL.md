---
name: build-graph-agent
description: Create graph-based IKEA chat subagents using repository standards.
---

# build-graph-agent

Create a new IKEA chat subagent implemented as a PydanticAI beta graph, using the repository's required directory structure, test strategy, and shared CLI/registry contracts.

## When to use

Use this skill whenever the user asks to:

- add a new subagent under `src/ikea_agent/chat/subagents/`
- implement a capability as a graph-based subagent
- scaffold tools/prompt/tests for a new subagent

This is the standard path for creating new subagents in this repository.

## Authoritative beta-graph references

Use these docs as the source of truth when generating graph patterns:

- https://ai.pydantic.dev/graph/beta/
- https://ai.pydantic.dev/graph/beta/steps/
- https://ai.pydantic.dev/graph/beta/parallel/
- https://ai.pydantic.dev/graph/beta/joins/
- https://ai.pydantic.dev/graph/beta/decisions/
- https://ai.pydantic.dev/api/pydantic_graph/beta_graph/

## High-level behavior

1. Capture intent for the subagent:
- `agent_name`
- high-level user story
- required input from parent context
- required output back to parent context
- user-described flow narrative (major steps, branching points, failure paths)

2. Capture execution design:
- sequential vs parallel branches
- explicit fan-out/fan-in (join) behavior where appropriate
- failure handling and partial-result behavior
- decision-node routing behavior (matching rules, branch priority, catch-all branch)

3. Capture tool scope:
- list required tools
- for each tool: implement now or stub now
- default to stubs when unclear

4. Generate implementation and tests in the required paths.

5. Register the subagent in the shared registry.

## Required output structure for each new subagent

For subagent `<agent_name>`, create:

- `src/ikea_agent/chat/subagents/<agent_name>/graph.py`
- `src/ikea_agent/chat/subagents/<agent_name>/nodes.py`
- `src/ikea_agent/chat/subagents/<agent_name>/prompt.md`
- `src/ikea_agent/chat/subagents/<agent_name>/tools/__init__.py`
- `src/ikea_agent/chat/subagents/<agent_name>/tools/...`
- `src/ikea_agent/chat/subagents/<agent_name>/__init__.py`
- `src/ikea_agent/chat/subagents/<agent_name>/README.md`

Create `types.py` only when internal data structures are non-trivial:

- `src/ikea_agent/chat/subagents/<agent_name>/types.py`

Use shared subagent infrastructure (create if missing, extend if present):

- `src/ikea_agent/chat/subagents/common.py`
- `src/ikea_agent/chat/subagents/registry.py`

## Shared CLI contract (single CLI for all subagents)

Do not create per-agent CLI modules.

Use a single shared CLI:

- `src/ikea_agent/chat/subagents/cli.py`

The CLI must support:

- selecting agent by name
- providing input as inline JSON/text and optionally file input
- JSON output by default
- non-zero exit code on errors

Expected invocation:

```bash
python -m ikea_agent.chat.subagents.cli --agent <agent_name> --input '<json-or-text>'
```

## Graph design requirements

- Use only Pydantic Graph **beta** APIs (`GraphBuilder`, `step`, `edge_from`, `decision`, `match`, `join`).
- Do **not** use `BaseNode`, `End`, or v1 `Graph(..., nodes=(...))` node-class wiring.
- Prefer small typed **step functions** in `nodes.py` (the filename can stay `nodes.py`, but contents must be beta steps).
- Use fan-out/fan-in for independent work streams.
- Add an explicit join node with deterministic merge behavior.
- Use `builder.decision()` where routing is conditional; branch with explicit match rules and branch labels.
- Define behavior for:
- empty branch outputs
- partial branch failure
- conflicting branch outputs

For parallel map flows, account for empty iterables (`downstream_join_id` pattern) so joins still run.

### Beta-only examples (from the floor-plan intake migration)

- Don't do this (v1 node API):
```python
class RouteInputNode(BaseNode[State, Deps, Output]):
    async def run(self, ctx) -> BaseNode[...] | End[Output]:
        ...
```

- Do this (beta steps + decisions):
```python
builder = GraphBuilder[State, Deps, Input, Output]()
route_step = builder.step(route_turn, node_id="route_turn")
route_decision = builder.decision(...).branch(
    builder.match(RouteSignal, matches=lambda s: s.kind == "ask_dimensions").to(ask_dimensions_step)
)
builder.add(
    builder.edge_from(builder.start_node).to(route_step),
    builder.edge_from(route_step).to(route_decision),
    builder.edge_from(ask_dimensions_step).to(builder.end_node),
)
graph = builder.build()
```

- Don't do this (v1 run style):
```python
graph.run_sync(RouteInputNode(payload=payload), state=State(), deps=deps)
```

- Do this (beta run style):
```python
await graph.run(state=State(), deps=deps, inputs=payload)
```

## Prompt requirements

- Store subagent prompt in `prompt.md`.
- Keep prompt concrete and output-oriented.
- Include expected output schema/shape in the prompt when useful.

## Subagent typing patterns (required)

Each generated subagent should define local typing aliases to reduce repeated annotations and improve errors:

1. A subagent-specific step context alias pattern in `types.py` (or `nodes.py` for trivial agents):
- pattern: `StepContext[<StateType>, None, <InputType>]`
- plus a generic alias for varying input type where practical

2. A typed callable alias/protocol for steps:
- async callable receiving the subagent context alias and returning typed output
- use per-step input/output generic parameters when practical

These aliases are local to each subagent and must not leak as parent-facing runtime contracts.

## Tool implementation requirements

- Put subagent-specific tools under `tools/`.
- Keep tool I/O typed.
- If tool behavior is uncertain, stub explicitly and leave a clear TODO.
- Generated stubs must be testable and deterministic.

## Testing requirements

Create typed pytest tests under:

- `tests/chat/subagents/<agent_name>/test_graph.py`
- `tests/chat/subagents/<agent_name>/test_nodes.py`
- `tests/chat/subagents/<agent_name>/test_tools.py`

Shared CLI tests go under:

- `tests/chat/subagents/test_cli.py`

Default test strategy:

- use PydanticAI `FunctionModel`-style deterministic mocks for model-driven behavior
- cover success path, error path, and join behavior
- cover at least one decision branch test (including catch-all behavior when configured)
- verify prompt-loading behavior and meaningful failures

## Flow documentation requirements (README + Mermaid)

For every generated subagent, include `README.md` with:

- concise user story and scope
- input and output contract summary
- tool inventory (implemented vs stubbed)
- decision table (condition -> branch -> outcome)
- Mermaid diagram of the graph flow and major decisions

Mermaid source should be either:

- generated from `graph.render(title=..., direction='LR')`, or
- written manually to mirror current flow when generation is not yet wired in tests

When decisions are present, ensure branch labels are represented clearly in the Mermaid flow.

## Shared helper default

Prefer function-based helpers in `common.py` over inheritance-heavy base classes.

At minimum, shared helpers should cover:

- prompt loading
- tool loading/wiring
- subagent construction/bootstrap

## Registration requirements

Every generated subagent must be discoverable from:

- `src/ikea_agent/chat/subagents/registry.py`

The shared CLI dispatches through this registry.

## AGENTS.md maintenance requirement

If this skill is added to a repo, ensure `AGENTS.md`:

- lists `build-graph-agent` under available skills
- marks it as the standard way to create new subagents
- references the “Adding Agents” section accordingly
