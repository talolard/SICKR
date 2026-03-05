from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tal_maria_ikea.tools.contracts import ToolExecutionResult
from tal_maria_ikea.tools.floor_planner_models import FloorPlanRequest
from tal_maria_ikea.tools.floor_planner_renderer import (
    FloorPlannerRenderError,
    FloorPlanRenderResult,
)
from tal_maria_ikea.tools.floor_planner_tool import FloorPlannerTool, register_floor_planner_tool


@dataclass(frozen=True, slots=True)
class _SuccessRenderer:
    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        _ = output_dir
        return FloorPlanRenderResult(
            output_png=Path("artifacts/floor_plans/example.png"),
            plan_name=request.plan_name,
            wall_count=1,
            door_count=0,
            window_count=0,
        )


@dataclass(frozen=True, slots=True)
class _FailRenderer:
    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        _ = (request, output_dir)
        msg = "renderer exploded"
        raise FloorPlannerRenderError(msg)


@dataclass(slots=True)
class _DummyAgent:
    decorated: list[Callable[[FloorPlanRequest], ToolExecutionResult]]

    def tool(
        self,
        function: Callable[[FloorPlanRequest], ToolExecutionResult],
    ) -> Callable[[FloorPlanRequest], ToolExecutionResult]:
        self.decorated.append(function)
        return function


def _minimal_request() -> FloorPlanRequest:
    return FloorPlanRequest.model_validate(
        {
            "plan_name": "tiny",
            "walls": [
                {
                    "id": "w1",
                    "start": {"x_m": 0.0, "y_m": 0.0},
                    "end": {"x_m": 1.0, "y_m": 0.0},
                    "thickness_m": 0.1,
                },
                {
                    "id": "w2",
                    "start": {"x_m": 1.0, "y_m": 0.0},
                    "end": {"x_m": 1.0, "y_m": 1.0},
                    "thickness_m": 0.1,
                },
                {
                    "id": "w3",
                    "start": {"x_m": 1.0, "y_m": 1.0},
                    "end": {"x_m": 0.0, "y_m": 1.0},
                    "thickness_m": 0.1,
                },
                {
                    "id": "w4",
                    "start": {"x_m": 0.0, "y_m": 1.0},
                    "end": {"x_m": 0.0, "y_m": 0.0},
                    "thickness_m": 0.1,
                },
            ],
        }
    )


def test_tool_returns_success_result() -> None:
    tool = FloorPlannerTool(renderer=_SuccessRenderer(), output_dir=Path("artifacts/unused"))

    result = tool.run(_minimal_request())

    assert isinstance(result, ToolExecutionResult)
    assert result.success is True
    assert result.output_path == Path("artifacts/floor_plans/example.png")


def test_tool_returns_error_result() -> None:
    tool = FloorPlannerTool(renderer=_FailRenderer(), output_dir=Path("artifacts/unused"))

    result = tool.run(_minimal_request())

    assert result.success is False
    assert result.errors == ("renderer exploded",)


def test_register_floor_planner_tool_decorates_callable() -> None:
    agent = _DummyAgent(decorated=[])
    tool = FloorPlannerTool(renderer=_SuccessRenderer(), output_dir=Path("artifacts/unused"))

    wrapped = register_floor_planner_tool(agent, tool)
    output = wrapped(_minimal_request())

    assert len(agent.decorated) == 1
    assert output.success is True
