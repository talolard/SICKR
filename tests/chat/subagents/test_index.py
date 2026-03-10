from __future__ import annotations

import pytest

from ikea_agent.chat.subagents.floor_plan_intake.agent import FloorPlannerSubgraphAgent
from ikea_agent.chat.subagents.index import (
    build_subagent_ag_ui_agent,
    describe_subagent,
    get_subgraph_agent,
    list_subagent_catalog,
)


def test_list_subagent_catalog_includes_floor_plan_intake() -> None:
    catalog = list_subagent_catalog()

    item = next(entry for entry in catalog if entry["name"] == "floor_plan_intake")
    assert item["agent_key"] == "subagent_floor_plan_intake"
    assert item["ag_ui_path"] == "/ag-ui/subagents/floor_plan_intake"


def test_describe_subagent_returns_prompt_mermaid_and_tools() -> None:
    metadata = describe_subagent("floor_plan_intake")

    assert metadata["name"] == "floor_plan_intake"
    assert "statediagram-v2" in metadata["mermaid"].lower()
    assert "Floor Plan Intake Subagent Prompt" in metadata["prompt_markdown"]
    assert metadata["tools"] == ["decide_floor_plan_intake_step", "render_floor_plan_draft"]


def test_get_subgraph_agent_raises_for_unknown() -> None:
    with pytest.raises(KeyError, match="Unknown subagent"):
        _ = get_subgraph_agent("unknown")


def test_build_subagent_ag_ui_agent_uses_subagent_prompt_instructions() -> None:
    agent = build_subagent_ag_ui_agent("floor_plan_intake")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "Floor Plan Intake Subagent Prompt" in instructions


class _FakeSettings:
    gemini_generation_model = "global-model"

    @staticmethod
    def subagent_model(name: str) -> str | None:
        if name == "floor_plan_intake":
            return "subagent-model"
        return None


def test_subagent_model_resolution_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    def _get_settings() -> _FakeSettings:
        return _FakeSettings()

    monkeypatch.setattr("ikea_agent.chat.subagents.base.get_settings", _get_settings)

    assert FloorPlannerSubgraphAgent.resolve_model_name(explicit_model="explicit") == "explicit"
    assert FloorPlannerSubgraphAgent.resolve_model_name() == "subagent-model"


class _GlobalOnlySettings:
    gemini_generation_model = "global-model"

    @staticmethod
    def subagent_model(name: str) -> None:
        _ = name


def test_subagent_model_resolution_falls_back_to_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _get_settings() -> _GlobalOnlySettings:
        return _GlobalOnlySettings()

    monkeypatch.setattr("ikea_agent.chat.subagents.base.get_settings", _get_settings)

    assert FloorPlannerSubgraphAgent.resolve_model_name() == "global-model"
