from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import BinaryContent, ToolReturn

from ikea_agent.tools.floorplanner.models import FloorPlanRequest
from ikea_agent.tools.floorplanner.renderer import FloorPlannerRenderError, FloorPlanRenderResult
from ikea_agent.tools.floorplanner.tool import FloorPlannerToolResult, render_floor_plan


def _minimal_request() -> FloorPlanRequest:
    return FloorPlanRequest.model_validate(
        {
            "elements": [
                {
                    "type": "wall",
                    "name": "tiny_wall_1",
                    "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "length_cm": 100.0,
                    "thickness_cm": 10.0,
                },
                {
                    "type": "wall",
                    "name": "tiny_wall_2",
                    "anchor_point_cm": {"x_cm": 100.0, "y_cm": 0.0},
                    "length_cm": 100.0,
                    "thickness_cm": 10.0,
                    "orientation_angle_deg": 90.0,
                },
                {
                    "type": "wall",
                    "name": "tiny_wall_3",
                    "anchor_point_cm": {"x_cm": 100.0, "y_cm": 100.0},
                    "length_cm": 100.0,
                    "thickness_cm": 10.0,
                    "orientation_angle_deg": 180.0,
                },
            ],
        }
    )


def test_render_floor_plan_returns_success_result(tmp_path: Path) -> None:
    request = _minimal_request()

    result = render_floor_plan(request, output_dir=tmp_path)

    assert isinstance(result, FloorPlannerToolResult)
    assert result.element_names == ["tiny_wall_1", "tiny_wall_2", "tiny_wall_3"]
    assert result.output_png_path == str(tmp_path / "floor_plan.png")


def test_render_floor_plan_returns_tool_return_when_requested(tmp_path: Path) -> None:
    request = _minimal_request().model_copy(update={"include_image_bytes": True})

    result = render_floor_plan(request, output_dir=tmp_path)

    assert isinstance(result, ToolReturn)
    assert result.metadata is not None
    assert result.metadata["element_names"] == ["tiny_wall_1", "tiny_wall_2", "tiny_wall_3"]
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert isinstance(result.content[0], BinaryContent)


def test_render_floor_plan_raises_value_error_from_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _minimal_request()

    def _raise_render_error(
        self: object,
        request: FloorPlanRequest,
        output_dir: Path,
    ) -> FloorPlanRenderResult:
        _ = (self, request, output_dir)
        msg = "renderer exploded"
        raise FloorPlannerRenderError(msg)

    monkeypatch.setattr(
        "ikea_agent.tools.floorplanner.renderer.FloorPlannerRenderer.render",
        _raise_render_error,
    )

    with pytest.raises(ValueError, match="Floor plan rendering failed"):
        render_floor_plan(request, output_dir=Path("artifacts/unused"))
