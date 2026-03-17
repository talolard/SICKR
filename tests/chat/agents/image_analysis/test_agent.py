from __future__ import annotations

from dataclasses import dataclass
from typing import Never, cast

from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.image_analysis.agent import (
    TOOL_NAMES,
    build_image_analysis_agent,
)
from ikea_agent.chat.agents.image_analysis.toolset import (
    DepthEstimationRunner,
    ImageAnalysisToolsetServices,
    ObjectDetectionRunner,
    RoomDetailAnalysisRunner,
    RoomPhotoAnalysisRunner,
    SegmentationRunner,
)


@dataclass(frozen=True, slots=True)
class _ImageAnalysisStub:
    async def __call__(self, **_: object) -> Never:
        raise RuntimeError("stub should not be invoked in builder-only test")


def test_image_analysis_agent_loads_prompt_instructions() -> None:
    agent = build_image_analysis_agent(explicit_model="gemini-2.0-flash")

    instructions = "\n".join(str(item) for item in agent._instructions)
    assert "room-image analysis specialist" in instructions
    assert "get_room_detail_details_from_photo" in instructions


def test_image_analysis_agent_registers_room_detail_tool() -> None:
    agent = build_image_analysis_agent(explicit_model="gemini-2.0-flash")

    image_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(image_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)


def test_image_analysis_agent_accepts_injected_toolset_services() -> None:
    services = ImageAnalysisToolsetServices(
        get_analysis_repository=lambda _runtime: None,
        detect_objects_in_image=cast("ObjectDetectionRunner", _ImageAnalysisStub()),
        estimate_depth_map=cast("DepthEstimationRunner", _ImageAnalysisStub()),
        segment_image_with_prompt=cast("SegmentationRunner", _ImageAnalysisStub()),
        analyze_room_photo=cast("RoomPhotoAnalysisRunner", _ImageAnalysisStub()),
        get_room_detail_details_from_photo=cast(
            "RoomDetailAnalysisRunner",
            _ImageAnalysisStub(),
        ),
    )

    agent = build_image_analysis_agent(
        explicit_model="gemini-2.0-flash",
        toolset_services=services,
    )

    image_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    assert set(TOOL_NAMES).issubset(image_toolset.tools)
