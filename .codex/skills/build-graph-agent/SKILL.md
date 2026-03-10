---
name: build-graph-agent
description: Create graph-based IKEA subagents using the class-based SubgraphAgent contract.
---

# build-graph-agent

Create a new IKEA chat subagent implemented as a Pydantic Graph beta graph with a direct,
class-based runtime contract.

## When to use

Use this skill whenever you need to:

- add a new subagent under `src/ikea_agent/chat/subagents/`
- implement a capability as a graph-based subagent
- scaffold prompt/tools/tests for a new subagent

## Required architecture

Every subagent must follow this structure:

- `src/ikea_agent/chat/subagents/base.py` provides shared `SubgraphAgent` behavior
- each subagent package defines one concrete class in `agent.py` that extends `SubgraphAgent`
- `src/ikea_agent/chat/subagents/index.py` explicitly lists subagents for discovery and routing

Do not use:

- registry pattern (`registry.py`)
- wrapper adapters (`web.py`)
- shared subagent CLI (`cli.py`)

## Required files for subagent `<agent_name>`

- `src/ikea_agent/chat/subagents/<agent_name>/agent.py`
- `src/ikea_agent/chat/subagents/<agent_name>/graph.py`
- `src/ikea_agent/chat/subagents/<agent_name>/nodes.py`
- `src/ikea_agent/chat/subagents/<agent_name>/prompt.md`
- `src/ikea_agent/chat/subagents/<agent_name>/tools/__init__.py`
- `src/ikea_agent/chat/subagents/<agent_name>/tools/...`
- `src/ikea_agent/chat/subagents/<agent_name>/README.md`

Optional when needed:

- `src/ikea_agent/chat/subagents/<agent_name>/types.py`

## Concrete class contract

Each subagent class must define:

- `subagent_name`
- `description`
- `prompt_path`
- `tool_names`
- `notes` (optional)
- `build_graph()`
- `build_state()`
- `build_deps(model_name=...)`
- `parse_user_input(user_message)`

Runtime behavior must come from `SubgraphAgent` base class:

- AG-UI adapter generation
- model resolution
- prompt loading and instruction creation
- metadata generation

## Prompt requirements

- store prompt in `prompt.md`
- use prompt content as runtime instruction base (not docs-only)
- append only minimal machine constraints programmatically when needed

## Model resolution requirements

Subagent model selection must follow:

1. explicit override from caller
2. per-subagent config override
3. global default generation model

## Graph requirements

- use Pydantic Graph **beta** APIs (`GraphBuilder`, `step`, `decision`, `match`, `join`)
- avoid v1 node wiring patterns (`BaseNode`, `End`, `run_sync`)
- execute graph with `await graph.run(state=..., deps=..., inputs=...)`

## Index and route requirements

After adding a subagent class:

1. add it explicitly to `src/ikea_agent/chat/subagents/index.py`
2. ensure backend routes continue to work via index-driven discovery:
   - `/api/subagents`
   - `/api/subagents/{name}/metadata`
   - `/ag-ui/subagents/{name}`

## Testing requirements

Add typed pytest coverage for:

- base contract behavior (`SubgraphAgent` model/prompt/metadata)
- index discovery and unknown-name errors
- subagent-specific graph behavior
- API route smoke for subagent endpoints

Tests must verify each subagent uses:

- its own prompt
- its own declared tool set
- its own graph metadata

## Done criteria for new subagent

- class-based subagent exists and is readable in one file (`agent.py`)
- subagent is explicitly listed in `index.py`
- no registry/web/cli indirection added
- metadata + AG-UI routes function end-to-end
- tests pass for new contract
