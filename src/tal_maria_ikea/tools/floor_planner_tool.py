"""Agent bridge and tool wrapper for floor-plan rendering."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from tal_maria_ikea.tools.contracts import ToolExecutionResult, ToolProtocol
from tal_maria_ikea.tools.floor_planner_models import FloorPlanRequest
from tal_maria_ikea.tools.floor_planner_renderer import (
    FloorPlannerRenderer,
    FloorPlannerRenderError,
    FloorPlanRenderResult,
)


class FloorPlanRendererProtocol(Protocol):
    """Structural protocol for renderers accepted by `FloorPlannerTool`."""

    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        """Render the requested plan to output directory."""


class AgentWithToolDecorator(Protocol):
    """Structural protocol for runtimes exposing a `.tool` decorator."""

    def tool(
        self,
        function: Callable[[FloorPlanRequest], ToolExecutionResult],
    ) -> Callable[[FloorPlanRequest], ToolExecutionResult]:
        """Register one callable as an agent tool."""


class FloorPlannerTool(ToolProtocol):
    """Domain tool that renders floor plans to local files."""

    def __init__(
        self, renderer: FloorPlanRendererProtocol | None = None, output_dir: Path | None = None
    ) -> None:
        self._renderer = renderer or FloorPlannerRenderer()
        self._output_dir = output_dir or Path("artifacts/floor_plans")

    def run(self, payload: object) -> ToolExecutionResult:
        """Render a floor plan and return the normalized tool response envelope."""

        if not isinstance(payload, FloorPlanRequest):
            msg = "Floor planner tool expects FloorPlanRequest payload"
            return ToolExecutionResult(
                tool_name="floor_planner",
                success=False,
                message=msg,
                errors=(msg,),
            )

        try:
            render_result = self._renderer.render(payload, self._output_dir)
        except FloorPlannerRenderError as exc:
            return ToolExecutionResult(
                tool_name="floor_planner",
                success=False,
                message="Floor plan rendering failed",
                errors=(str(exc),),
            )

        return ToolExecutionResult(
            tool_name="floor_planner",
            success=True,
            message=(
                "Rendered floor plan. Ask the user to confirm whether room shape and openings "
                "match their intent before proceeding."
            ),
            output_path=render_result.output_png,
            metadata={
                "plan_name": render_result.plan_name,
                "wall_count": render_result.wall_count,
                "door_count": render_result.door_count,
                "window_count": render_result.window_count,
            },
        )


def register_floor_planner_tool(
    agent: AgentWithToolDecorator, tool: FloorPlannerTool
) -> Callable[[FloorPlanRequest], ToolExecutionResult]:
    """Register floor planner as a decorated tool on pydantic-ai style agents.

    This function intentionally relies on duck-typing (`agent.tool`) so the tools
    package can stay independent from any particular agent runtime module.
    """

    @agent.tool
    def render_floor_plan(request: FloorPlanRequest) -> ToolExecutionResult:
        """Render a floor plan image from a typed request."""

        return tool.run(request)

    return render_floor_plan
