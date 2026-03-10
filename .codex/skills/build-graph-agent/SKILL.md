---
name: build-graph-agent
description: Create first-class IKEA agents using local pydantic-ai toolsets (agents-first runtime; no graph layer).
---

# build-graph-agent

This skill name is legacy. Use it to build **agents-first** capabilities.
Do not add `pydantic_graph` orchestration or `subagents/*` packages.

## When to use

Use this skill whenever you need to:

- add a new agent under `src/ikea_agent/chat/agents/`
- implement a capability as a plain `pydantic_ai.Agent`
- scaffold prompt/toolset/tests for a new agent

## Required architecture

Every agent must follow this structure:

- `src/ikea_agent/chat/agents/<agent_name>/agent.py`
- `src/ikea_agent/chat/agents/<agent_name>/deps.py`
- `src/ikea_agent/chat/agents/<agent_name>/toolset.py`
- `src/ikea_agent/chat/agents/<agent_name>/prompt.md`
- optional `README.md` for capability notes

Global registration must be explicit in `src/ikea_agent/chat/agents/index.py`:

- catalog item (`name`, `agent_key`, `ag_ui_path`, `web_path`)
- metadata builder (`describe_agent`)
- runtime builder (`build_agent_ag_ui_agent`)

Do not add:

- graph builder/node files
- registry indirection
- shared cross-agent tool registries

## Tool requirements

- Tools remain in `src/ikea_agent/tools/` for domain logic.
- Agent-facing wrappers live in local `toolset.py`.
- Build one `FunctionToolset[...]` per agent and register tool names explicitly.
- Tool input/output must be typed and JSON-serializable.

## Model resolution requirements

Agent model selection must follow:

1. explicit override from caller
2. per-agent config override (`settings.agent_model(agent_name)`)
3. global default generation model

## Route requirements

After adding an agent, ensure these routes work:

- `/api/agents`
- `/api/agents/{name}/metadata`
- `/ag-ui/agents/{name}`
- `/agents/{name}/chat/`

## Testing requirements

Add typed pytest coverage for:

- index discovery and unknown-name errors
- prompt loading and instructions wiring
- local toolset registration
- API route smoke for agent endpoints

## Done criteria for new agent

- agent package exists under `chat/agents/<agent_name>/`
- agent is listed in `chat/agents/index.py`
- no graph/subagent runtime introduced
- metadata + AG-UI routes function end-to-end
- tests pass and `make tidy` is clean
