from __future__ import annotations

import pytest

from ikea_agent.chat.agents.floor_plan_intake.agent import resolve_model_name
from ikea_agent.chat.agents.index import (
    build_agent_ag_ui_agent,
    describe_agent,
    get_agent,
    list_agent_catalog,
)
from ikea_agent.chat.agents.search.agent import (
    DEFAULT_SEARCH_MODEL,
)
from ikea_agent.chat.agents.search.agent import (
    resolve_model_name as resolve_search_model_name,
)


def test_list_agent_catalog_includes_floor_plan_intake() -> None:
    catalog = list_agent_catalog()

    item = next(entry for entry in catalog if entry["name"] == "floor_plan_intake")
    assert item["agent_key"] == "agent_floor_plan_intake"
    assert item["ag_ui_path"] == "/ag-ui/agents/floor_plan_intake"


def test_describe_agent_returns_prompt_and_tools() -> None:
    metadata = describe_agent("floor_plan_intake")

    assert metadata["name"] == "floor_plan_intake"
    assert "floor-plan intake specialist" in metadata["prompt_markdown"]
    assert "render_floor_plan" in metadata["tools"]


def test_get_agent_raises_for_unknown() -> None:
    with pytest.raises(KeyError, match="Unknown agent"):
        _ = get_agent("unknown")


def test_build_agent_ag_ui_agent_uses_prompt_instructions() -> None:
    agent = build_agent_ag_ui_agent("floor_plan_intake")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "floor-plan intake specialist" in instructions


def test_get_agent_returns_catalog_item() -> None:
    item = get_agent("floor_plan_intake")
    assert item["name"] == "floor_plan_intake"
    assert item["agent_key"] == "agent_floor_plan_intake"


class _FakeSettings:
    gemini_generation_model = "global-model"

    @staticmethod
    def agent_model(name: str) -> str | None:
        if name == "floor_plan_intake":
            return "agent-model"
        return None


def test_agent_model_resolution_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    def _get_settings() -> _FakeSettings:
        return _FakeSettings()

    monkeypatch.setattr(
        "ikea_agent.chat.agents.floor_plan_intake.agent.get_settings",
        _get_settings,
    )

    assert resolve_model_name(explicit_model="explicit") == "explicit"
    assert resolve_model_name() == "agent-model"


class _GlobalOnlySettings:
    gemini_generation_model = "global-model"

    @staticmethod
    def agent_model(name: str) -> None:
        _ = name


def test_agent_model_resolution_falls_back_to_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _get_settings() -> _GlobalOnlySettings:
        return _GlobalOnlySettings()

    monkeypatch.setattr(
        "ikea_agent.chat.agents.floor_plan_intake.agent.get_settings",
        _get_settings,
    )

    assert resolve_model_name() == "global-model"


class _SearchOnlySettings:
    gemini_generation_model = "global-model"

    @staticmethod
    def agent_model(name: str) -> None:
        _ = name


def test_search_agent_model_resolution_falls_back_to_search_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _get_settings() -> _SearchOnlySettings:
        return _SearchOnlySettings()

    monkeypatch.setattr(
        "ikea_agent.chat.agents.search.agent.get_settings",
        _get_settings,
    )

    assert resolve_search_model_name() == DEFAULT_SEARCH_MODEL
