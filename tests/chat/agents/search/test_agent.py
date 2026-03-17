from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.search.agent import TOOL_NAMES, build_search_agent
from ikea_agent.chat.agents.search.toolset import SearchToolsetServices
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.shared.types import SearchBatchToolResult


@dataclass(frozen=True, slots=True)
class _SearchPipelineStub:
    async def __call__(
        self,
        *,
        runtime: ChatRuntime,
        queries: list[object],
    ) -> SearchBatchToolResult:
        _ = (runtime, queries)
        return SearchBatchToolResult(queries=[])


def test_search_agent_loads_prompt_instructions() -> None:
    agent = build_search_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "Home Solutions Architect" in instructions
    assert "run_search_graph" in instructions
    assert "broader IKEA catalog" in instructions
    assert "semantic descriptions, short keyword phrases" in instructions
    assert "Do **not** invent unsupported IKEA products" in instructions
    assert "Do not mention a needed support product and then drop it." in instructions


def test_search_agent_registers_search_tools() -> None:
    agent = build_search_agent(explicit_model="gemini-2.0-flash")

    search_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(search_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)


def test_search_agent_accepts_injected_toolset_services() -> None:
    services = SearchToolsetServices(
        run_search_batch=_SearchPipelineStub(),
        get_search_repository=lambda _runtime: None,
        get_room_3d_repository=lambda _runtime: None,
    )

    agent = build_search_agent(
        explicit_model="gemini-2.0-flash",
        toolset_services=services,
    )

    search_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    assert set(TOOL_NAMES).issubset(search_toolset.tools)
