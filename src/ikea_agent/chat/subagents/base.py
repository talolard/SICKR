"""Shared class-based contract for graph-backed subagents."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from time import time
from typing import ClassVar, Literal, Protocol, TypedDict, TypeVar, cast

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ikea_agent.config import get_settings

StateT = TypeVar("StateT")
DepsT = TypeVar("DepsT")
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
SubagentPersistenceMode = Literal["state_per_thread", "data_per_turn", "disabled"]


class SupportsSubgraphRuntime(Protocol[StateT, DepsT, InputT, OutputT]):
    """Minimal graph protocol needed by the shared subagent runtime."""

    async def run(self, *, state: StateT, deps: DepsT, inputs: InputT) -> OutputT:
        """Execute one graph turn and return typed output."""

    def render(self, *, title: str, direction: str) -> str:
        """Render graph structure for metadata and documentation."""


class SubagentCatalogItem(TypedDict):
    """Subagent fields used by frontend navigation and runtime routing."""

    name: str
    description: str
    agent_key: str
    ag_ui_path: str
    web_path: str


class SubagentDescription(SubagentCatalogItem):
    """Full subagent metadata payload returned by backend endpoints."""

    prompt_markdown: str
    mermaid: str
    tools: list[str]
    notes: str


class SubagentTurnRecord(BaseModel):
    """Per-turn conversational record captured for subagent runs."""

    timestamp_ms: int
    thread_id: str
    run_id: str | None = None
    user_message: str
    assistant_message: str
    output_payload: dict[str, object]
    notes: list[str]


class SupportsPersistentSubagentState(Protocol):
    """Minimal shared-state surface needed for subagent persistence hooks."""

    thread_id: str | None
    run_id: str | None
    subagent_state: dict[str, dict[str, dict[str, object]]]
    subagent_turn_history: dict[str, dict[str, list[dict[str, object]]]]


class SubgraphAgent[StateT, DepsT, InputT, OutputT](Agent[None, str]):
    """Class-based graph subagent that builds AG-UI adapters from one graph contract."""

    subagent_name: ClassVar[str]
    description: ClassVar[str]
    prompt_path: ClassVar[Path]
    tool_names: ClassVar[tuple[str, ...]] = ()
    notes: ClassVar[str] = ""
    persistence_mode: ClassVar[SubagentPersistenceMode | None] = None
    capture_turn_history: ClassVar[bool | None] = None

    @classmethod
    def agent_key(cls) -> str:
        """Stable CopilotKit agent key for this subagent."""

        return f"subagent_{cls.subagent_name}"

    @classmethod
    def ag_ui_path(cls) -> str:
        """Stable AG-UI endpoint path for this subagent."""

        return f"/ag-ui/subagents/{cls.subagent_name}"

    @classmethod
    def web_path(cls) -> str:
        """Stable web-chat endpoint path for this subagent."""

        return f"/subagents/{cls.subagent_name}/chat/"

    @classmethod
    def read_prompt_markdown(cls) -> str:
        """Load and validate prompt markdown for this subagent."""

        if not cls.prompt_path.exists():
            msg = f"Prompt file does not exist: {cls.prompt_path}"
            raise FileNotFoundError(msg)
        return cls.prompt_path.read_text(encoding="utf-8")

    @classmethod
    def _instruction_text_from_prompt(cls) -> str:
        raw = cls.read_prompt_markdown().strip()
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                raw = raw[end + 3 :].lstrip("\n")
        return raw.strip()

    @classmethod
    def build_instructions(cls) -> str:
        """Build runtime instructions for this subagent."""

        return cls._instruction_text_from_prompt()

    @classmethod
    def resolve_model_name(cls, *, explicit_model: str | None = None) -> str:
        """Resolve subagent model using explicit override, subagent config, then global default."""

        if explicit_model:
            return explicit_model
        settings = get_settings()
        configured_model = settings.subagent_model(cls.subagent_name)
        if configured_model:
            return configured_model
        return settings.gemini_generation_model

    @classmethod
    def resolve_persistence_mode(cls) -> SubagentPersistenceMode:
        """Resolve persistence mode using class override, config override, then default."""

        if cls.persistence_mode is not None:
            return cls.persistence_mode
        configured = get_settings().subagent_persistence_mode(cls.subagent_name)
        if configured is not None:
            return configured
        return "state_per_thread"

    @classmethod
    def resolve_capture_turn_history(cls) -> bool:
        """Resolve turn-history capture policy using class/config overrides then default."""

        if cls.capture_turn_history is not None:
            return cls.capture_turn_history
        configured = get_settings().subagent_capture_turn_history(cls.subagent_name)
        if configured is not None:
            return configured
        return True

    @classmethod
    @abstractmethod
    def build_graph(cls) -> object:
        """Build and return the subagent graph instance."""

    @classmethod
    @abstractmethod
    def build_state(cls) -> StateT:
        """Return the initial graph state for one run."""

    @classmethod
    @abstractmethod
    def build_deps(cls, *, model_name: str) -> DepsT:
        """Build graph dependencies for one run."""

    @classmethod
    @abstractmethod
    def parse_user_input(cls, user_message: str) -> InputT:
        """Convert latest user message into typed graph input."""

    @classmethod
    def hydrate_state(
        cls,
        payload: Mapping[str, object] | None,
    ) -> StateT:
        """Hydrate graph state from persisted payload using Pydantic/dataclass defaults."""

        if payload is None:
            return cls.build_state()

        template = cls.build_state()
        state_type = type(template)
        if hasattr(state_type, "model_validate"):
            validated = state_type.model_validate(payload)
            return cast("StateT", validated)

        if is_dataclass(template):
            field_names = {item.name for item in fields(template)}
            kwargs = {name: payload[name] for name in field_names if name in payload}
            return cast("StateT", state_type(**kwargs))

        msg = (
            f"Subagent `{cls.subagent_name}` state type `{state_type.__name__}` does not support "
            "default hydration. Override `hydrate_state` for custom behavior."
        )
        raise TypeError(msg)

    @classmethod
    def serialize_state(
        cls,
        state: StateT,
    ) -> dict[str, object] | None:
        """Serialize graph state using Pydantic/dataclass defaults."""

        if hasattr(state, "model_dump"):
            dumped = state.model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped

        if is_dataclass(state):
            return cast("dict[str, object]", asdict(state))

        msg = (
            f"Subagent `{cls.subagent_name}` state type `{type(state).__name__}` does not support "
            "default serialization. Override `serialize_state` for custom behavior."
        )
        raise TypeError(msg)

    @classmethod
    def build_turn_notes(
        cls,
        *,
        user_message: str,
        output: object,
        state: StateT,
    ) -> list[str]:
        """Return optional high-signal notes for turn history records."""

        _ = (user_message, output, state)
        return []

    @classmethod
    def output_to_json(cls, output: object) -> dict[str, object]:
        """Convert graph output to a JSON-safe mapping."""

        if hasattr(output, "model_dump"):
            dumped = output.model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped
        if isinstance(output, dict):
            return dict(output)
        return {"assistant_message": str(output)}

    @classmethod
    def extract_assistant_message(cls, output: object) -> str:
        """Extract assistant text from graph output for AG-UI response."""

        payload = cls.output_to_json(output)
        value = payload.get("assistant_message")
        if isinstance(value, str) and value.strip():
            return value
        return f"{cls.subagent_name} produced no assistant message."

    @classmethod
    async def run_one_turn(
        cls,
        *,
        user_message: str,
        model_name: str,
        persistent_state: SupportsPersistentSubagentState | None = None,
    ) -> OutputT:
        """Run one graph turn using typed state/deps/input builders."""

        graph = cast(
            "SupportsSubgraphRuntime[StateT, DepsT, InputT, OutputT]",
            cls.build_graph(),
        )
        mode = cls.resolve_persistence_mode()
        keep_history = cls.resolve_capture_turn_history()

        state = cls._load_state_for_turn(
            persistent_state=persistent_state,
            mode=mode,
        )
        output = await graph.run(
            state=state,
            deps=cls.build_deps(model_name=model_name),
            inputs=cls.parse_user_input(user_message),
        )
        if mode == "state_per_thread":
            cls._save_state_after_turn(
                persistent_state=persistent_state,
                state=state,
            )

        if keep_history:
            cls._append_turn_history_record(
                persistent_state=persistent_state,
                user_message=user_message,
                output=output,
                state=state,
            )

        return output

    @classmethod
    def _load_state_for_turn(
        cls,
        *,
        persistent_state: SupportsPersistentSubagentState | None,
        mode: SubagentPersistenceMode,
    ) -> StateT:
        if mode != "state_per_thread":
            return cls.build_state()

        if persistent_state is None or persistent_state.thread_id is None:
            return cls.build_state()

        by_subagent = persistent_state.subagent_state.get(cls.subagent_name, {})
        raw_payload = by_subagent.get(persistent_state.thread_id)
        payload = raw_payload if isinstance(raw_payload, Mapping) else None
        return cls.hydrate_state(payload)

    @classmethod
    def _save_state_after_turn(
        cls,
        *,
        persistent_state: SupportsPersistentSubagentState | None,
        state: StateT,
    ) -> None:
        if persistent_state is None or persistent_state.thread_id is None:
            return

        by_subagent = persistent_state.subagent_state.setdefault(cls.subagent_name, {})
        payload = cls.serialize_state(state)
        if payload is None:
            by_subagent.pop(persistent_state.thread_id, None)
            return
        by_subagent[persistent_state.thread_id] = payload

    @classmethod
    def _append_turn_history_record(
        cls,
        *,
        persistent_state: SupportsPersistentSubagentState | None,
        user_message: str,
        output: object,
        state: StateT,
    ) -> None:
        if persistent_state is None or persistent_state.thread_id is None:
            return

        by_subagent = persistent_state.subagent_turn_history.setdefault(cls.subagent_name, {})
        thread_history = by_subagent.setdefault(persistent_state.thread_id, [])
        output_payload = cls.output_to_json(output)
        record = SubagentTurnRecord(
            timestamp_ms=int(time() * 1000),
            thread_id=persistent_state.thread_id,
            run_id=persistent_state.run_id,
            user_message=user_message,
            assistant_message=cls.extract_assistant_message(output),
            output_payload=output_payload,
            notes=cls.build_turn_notes(
                user_message=user_message,
                output=output,
                state=state,
            ),
        )
        thread_history.append(record.model_dump(mode="json"))

    @classmethod
    def build_catalog_item(cls) -> SubagentCatalogItem:
        """Build catalog metadata used by UI navigation and runtime routing."""

        return SubagentCatalogItem(
            name=cls.subagent_name,
            description=cls.description,
            agent_key=cls.agent_key(),
            ag_ui_path=cls.ag_ui_path(),
            web_path=cls.web_path(),
        )

    @classmethod
    def build_metadata(cls) -> SubagentDescription:
        """Build full metadata payload for subagent inspection."""

        graph = cast(
            "SupportsSubgraphRuntime[StateT, DepsT, InputT, OutputT]",
            cls.build_graph(),
        )
        mermaid = graph.render(title=cls.subagent_name, direction="LR")
        return SubagentDescription(
            name=cls.subagent_name,
            description=cls.description,
            agent_key=cls.agent_key(),
            ag_ui_path=cls.ag_ui_path(),
            web_path=cls.web_path(),
            prompt_markdown=cls.read_prompt_markdown(),
            mermaid=mermaid,
            tools=list(cls.tool_names),
            notes=cls.notes,
        )

    @classmethod
    def build_agent(
        cls,
        *,
        explicit_model: str | None = None,
        persistent_state: SupportsPersistentSubagentState | None = None,
    ) -> Agent[None, str]:
        """Build a pydantic-ai Agent that dispatches one turn into this subgraph."""

        resolved_model_name = cls.resolve_model_name(explicit_model=explicit_model)
        subgraph_cls = cast("type[SubgraphAgent[object, object, object, object]]", cls)
        model = FunctionModel(
            _build_subgraph_function(
                subgraph_cls,
                model_name=resolved_model_name,
                persistent_state=persistent_state,
            ),
            stream_function=_build_subgraph_stream_function(
                subgraph_cls,
                model_name=resolved_model_name,
                persistent_state=persistent_state,
            ),
            model_name=cls.agent_key(),
        )
        return cls(
            model=model,
            deps_type=type(None),
            output_type=str,
            instructions=cls.build_instructions(),
        )


def _build_subgraph_function(
    subgraph_cls: type[SubgraphAgent],
    *,
    model_name: str,
    persistent_state: SupportsPersistentSubagentState | None,
) -> Callable[[list[ModelMessage], AgentInfo], Awaitable[ModelResponse]]:
    async def _run(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        _ = info
        user_message = _latest_user_prompt_text(messages)
        output = await subgraph_cls.run_one_turn(
            user_message=user_message,
            model_name=model_name,
            persistent_state=persistent_state,
        )
        assistant_text = subgraph_cls.extract_assistant_message(output)
        return ModelResponse(
            parts=[TextPart(content=assistant_text)],
            model_name=f"{subgraph_cls.agent_key()}-wrapper",
        )

    return _run


def _build_subgraph_stream_function(
    subgraph_cls: type[SubgraphAgent],
    *,
    model_name: str,
    persistent_state: SupportsPersistentSubagentState | None,
) -> Callable[[list[ModelMessage], AgentInfo], AsyncIterator[str]]:
    async def _run_stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        _ = info
        user_message = _latest_user_prompt_text(messages)
        output = await subgraph_cls.run_one_turn(
            user_message=user_message,
            model_name=model_name,
            persistent_state=persistent_state,
        )
        yield subgraph_cls.extract_assistant_message(output)

    return _run_stream


def _latest_user_prompt_text(messages: list[ModelMessage]) -> str:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        content = _first_user_prompt_content(message.parts)
        if content is not None and content.strip():
            return content
    return ""


def _first_user_prompt_content(parts: Sequence[ModelRequestPart]) -> str | None:
    for part in parts:
        if isinstance(part, UserPromptPart):
            if isinstance(part.content, str):
                return part.content
            fragments = [item for item in part.content if isinstance(item, str)]
            return "\n".join(fragments)
    return None


__all__ = [
    "SubagentCatalogItem",
    "SubagentDescription",
    "SubagentPersistenceMode",
    "SubagentTurnRecord",
    "SubgraphAgent",
    "SupportsPersistentSubagentState",
]
