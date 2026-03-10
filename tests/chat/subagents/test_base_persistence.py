from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from ikea_agent.chat.subagents.base import SubgraphAgent


@dataclass(slots=True)
class _CounterState:
    counter: int = 0


class _CounterStateModel(BaseModel):
    counter: int = 0


class _MemoryState:
    def __init__(self, thread_id: str | None) -> None:
        self.thread_id = thread_id
        self.run_id: str | None = "run-1"
        self.subagent_state: dict[str, dict[str, dict[str, object]]] = {}
        self.subagent_turn_history: dict[str, dict[str, list[dict[str, object]]]] = {}


class _GraphDataclass:
    async def run(
        self,
        *,
        state: _CounterState,
        deps: None,
        inputs: str,
    ) -> dict[str, object]:
        _ = (deps, inputs)
        state.counter += 1
        return {"assistant_message": f"count={state.counter}"}

    def render(self, *, title: str, direction: str) -> str:
        _ = (title, direction)
        return "stateDiagram-v2"


class _GraphPydantic:
    async def run(
        self,
        *,
        state: _CounterStateModel,
        deps: None,
        inputs: str,
    ) -> dict[str, object]:
        _ = (deps, inputs)
        state.counter += 1
        return {"assistant_message": f"count={state.counter}"}

    def render(self, *, title: str, direction: str) -> str:
        _ = (title, direction)
        return "stateDiagram-v2"


class _DataclassPersistentAgent(SubgraphAgent[_CounterState, None, str, dict[str, object]]):
    subagent_name = "dataclass_persistent"
    description = "test"
    prompt_path = __file__  # not used in tests

    @classmethod
    def build_graph(cls) -> _GraphDataclass:
        return _GraphDataclass()

    @classmethod
    def build_state(cls) -> _CounterState:
        return _CounterState()

    @classmethod
    def build_deps(cls, *, model_name: str) -> None:
        _ = model_name

    @classmethod
    def parse_user_input(cls, user_message: str) -> str:
        return user_message


class _PydanticPersistentAgent(SubgraphAgent[_CounterStateModel, None, str, dict[str, object]]):
    subagent_name = "pydantic_persistent"
    description = "test"
    prompt_path = __file__  # not used in tests

    @classmethod
    def build_graph(cls) -> _GraphPydantic:
        return _GraphPydantic()

    @classmethod
    def build_state(cls) -> _CounterStateModel:
        return _CounterStateModel()

    @classmethod
    def build_deps(cls, *, model_name: str) -> None:
        _ = model_name

    @classmethod
    def parse_user_input(cls, user_message: str) -> str:
        return user_message


class _DataPerTurnAgent(_DataclassPersistentAgent):
    subagent_name = "data_per_turn"
    persistence_mode = "data_per_turn"


class _DisabledAgent(_DataclassPersistentAgent):
    subagent_name = "disabled"
    persistence_mode = "disabled"


class _NotesAgent(_DataclassPersistentAgent):
    subagent_name = "notes"

    @classmethod
    def build_turn_notes(
        cls,
        *,
        user_message: str,
        output: object,
        state: _CounterState,
    ) -> list[str]:
        _ = output
        return [f"user={user_message}", f"counter={state.counter}"]


@pytest.mark.anyio
async def test_default_state_per_thread_persists_dataclass_state() -> None:
    memory = _MemoryState(thread_id="thread-1")

    first = await _DataclassPersistentAgent.run_one_turn(
        user_message="a",
        model_name="model",
        persistent_state=memory,
    )
    second = await _DataclassPersistentAgent.run_one_turn(
        user_message="b",
        model_name="model",
        persistent_state=memory,
    )

    assert first["assistant_message"] == "count=1"
    assert second["assistant_message"] == "count=2"
    assert memory.subagent_state["dataclass_persistent"]["thread-1"]["counter"] == 2


@pytest.mark.anyio
async def test_default_state_per_thread_persists_pydantic_state() -> None:
    memory = _MemoryState(thread_id="thread-1")

    _ = await _PydanticPersistentAgent.run_one_turn(
        user_message="a",
        model_name="model",
        persistent_state=memory,
    )
    second = await _PydanticPersistentAgent.run_one_turn(
        user_message="b",
        model_name="model",
        persistent_state=memory,
    )

    assert second["assistant_message"] == "count=2"


@pytest.mark.anyio
async def test_data_per_turn_mode_does_not_persist_state_but_keeps_history() -> None:
    memory = _MemoryState(thread_id="thread-1")

    first = await _DataPerTurnAgent.run_one_turn(
        user_message="a",
        model_name="model",
        persistent_state=memory,
    )
    second = await _DataPerTurnAgent.run_one_turn(
        user_message="b",
        model_name="model",
        persistent_state=memory,
    )

    assert first["assistant_message"] == "count=1"
    assert second["assistant_message"] == "count=1"
    assert "data_per_turn" not in memory.subagent_state
    assert len(memory.subagent_turn_history["data_per_turn"]["thread-1"]) == 2


@pytest.mark.anyio
async def test_disabled_mode_does_not_persist_state() -> None:
    memory = _MemoryState(thread_id="thread-1")

    first = await _DisabledAgent.run_one_turn(
        user_message="a",
        model_name="model",
        persistent_state=memory,
    )
    second = await _DisabledAgent.run_one_turn(
        user_message="b",
        model_name="model",
        persistent_state=memory,
    )

    assert first["assistant_message"] == "count=1"
    assert second["assistant_message"] == "count=1"
    assert "disabled" not in memory.subagent_state


@pytest.mark.anyio
async def test_turn_history_capture_includes_notes() -> None:
    memory = _MemoryState(thread_id="thread-1")

    _ = await _NotesAgent.run_one_turn(
        user_message="hello",
        model_name="model",
        persistent_state=memory,
    )

    history = memory.subagent_turn_history["notes"]["thread-1"]
    assert len(history) == 1
    assert history[0]["notes"] == ["user=hello", "counter=1"]


class _SettingsFromConfig:
    gemini_generation_model = "global"

    @staticmethod
    def subagent_model(name: str) -> None:
        _ = name

    @staticmethod
    def subagent_persistence_mode(name: str) -> str | None:
        if name == "configurable":
            return "data_per_turn"
        return None

    @staticmethod
    def subagent_capture_turn_history(name: str) -> bool | None:
        if name == "configurable":
            return False
        return None


class _ConfigurableAgent(_DataclassPersistentAgent):
    subagent_name = "configurable"


class _ClassOverrideAgent(_ConfigurableAgent):
    subagent_name = "override"
    persistence_mode = "disabled"
    capture_turn_history = True


def test_persistence_policy_resolves_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    def _get_settings() -> _SettingsFromConfig:
        return _SettingsFromConfig()

    monkeypatch.setattr("ikea_agent.chat.subagents.base.get_settings", _get_settings)

    assert _ConfigurableAgent.resolve_persistence_mode() == "data_per_turn"
    assert _ConfigurableAgent.resolve_capture_turn_history() is False


def test_class_override_beats_config(monkeypatch: pytest.MonkeyPatch) -> None:
    def _get_settings() -> _SettingsFromConfig:
        return _SettingsFromConfig()

    monkeypatch.setattr("ikea_agent.chat.subagents.base.get_settings", _get_settings)

    assert _ClassOverrideAgent.resolve_persistence_mode() == "disabled"
    assert _ClassOverrideAgent.resolve_capture_turn_history() is True
