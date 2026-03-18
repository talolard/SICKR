"""Direct, non-pytest harness for live floor-plan intake evals."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from evals.base import (
    AgentEvalHarness,
    extract_message_tool_call_captures,
    extract_message_tool_return_captures,
)
from evals.floor_plan_intake.types import (
    FloorPlanIntakeEvalInput,
    FloorPlanIntakeEvalRunCapture,
)
from ikea_agent.chat.agents.floor_plan_intake.agent import build_floor_plan_intake_agent
from ikea_agent.chat.agents.floor_plan_intake.deps import FloorPlanIntakeDeps
from ikea_agent.chat.agents.floor_plan_intake.toolset import (
    FloorPlanIntakeToolsetServices,
)
from ikea_agent.chat.agents.state import FloorPlanIntakeAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.floorplanner.scene_store import FloorPlanSceneStore
from ikea_agent.tools.floorplanner.tool import render_floor_plan as run_floor_planner


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    """Minimal runtime for floor-plan evals.

    The harness intentionally omits persistence so evals exercise the real agent/tool
    behavior without needing a writable runtime DuckDB.
    """


def _build_toolset_services() -> FloorPlanIntakeToolsetServices:
    return FloorPlanIntakeToolsetServices(
        render_floor_plan=run_floor_planner,
        get_floor_plan_repository=lambda _runtime: None,
    )


def _build_stub_deps(root_dir: Path) -> FloorPlanIntakeDeps:
    return FloorPlanIntakeDeps(
        runtime=cast("ChatRuntime", _RuntimeStub()),
        attachment_store=AttachmentStore(root_dir),
        floor_plan_scene_store=FloorPlanSceneStore(),
        state=FloorPlanIntakeAgentState(
            session_id="eval-session",
            thread_id="eval-thread",
            run_id="eval-run",
        ),
    )


class FloorPlanIntakeEvalHarness(AgentEvalHarness[FloorPlanIntakeEvalInput, str]):
    """Run the real floor-plan intake agent with persistence disabled."""

    async def capture_case(
        self,
        inputs: FloorPlanIntakeEvalInput,
    ) -> FloorPlanIntakeEvalRunCapture:
        """Execute one live floor-plan run and return the captured transcript artifacts."""

        agent = build_floor_plan_intake_agent(toolset_services=_build_toolset_services())
        with tempfile.TemporaryDirectory(prefix="floor-plan-eval-attachments-") as tmp_dir:
            deps = _build_stub_deps(Path(tmp_dir))
            result = await agent.run(inputs.user_message, deps=deps)
            messages = result.all_messages()
            return FloorPlanIntakeEvalRunCapture(
                final_output=result.output,
                message_tool_calls=extract_message_tool_call_captures(messages),
                message_tool_returns=extract_message_tool_return_captures(messages),
            )

    async def run_case(self, inputs: FloorPlanIntakeEvalInput) -> str:
        """Execute one live floor-plan intake eval case."""

        capture = await self.capture_case(inputs)
        return capture.final_output
