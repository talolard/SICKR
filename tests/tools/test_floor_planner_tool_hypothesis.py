from __future__ import annotations

from pathlib import Path

import hypothesis.strategies as st
from hypothesis import given, settings

from ikea_agent.tools.floorplanner.models import FloorPlanRenderRequest
from ikea_agent.tools.floorplanner.tool import render_floor_plan


@st.composite
def baseline_scene_payloads(draw: st.DrawFn) -> dict[str, object]:
    width = draw(st.floats(min_value=200.0, max_value=600.0, allow_nan=False, allow_infinity=False))
    depth = draw(st.floats(min_value=180.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    height = draw(
        st.floats(min_value=220.0, max_value=320.0, allow_nan=False, allow_infinity=False)
    )

    return {
        "scene": {
            "scene_level": "baseline",
            "architecture": {
                "dimensions_cm": {
                    "length_x_cm": width,
                    "depth_y_cm": depth,
                    "height_z_cm": height,
                },
                "walls": [
                    {
                        "wall_id": "w1",
                        "start_cm": {"x_cm": 0.0, "y_cm": 0.0},
                        "end_cm": {"x_cm": width, "y_cm": 0.0},
                    },
                    {
                        "wall_id": "w2",
                        "start_cm": {"x_cm": width, "y_cm": 0.0},
                        "end_cm": {"x_cm": width, "y_cm": depth},
                    },
                    {
                        "wall_id": "w3",
                        "start_cm": {"x_cm": width, "y_cm": depth},
                        "end_cm": {"x_cm": 0.0, "y_cm": depth},
                    },
                ],
            },
            "placements": [],
        },
        "include_image_bytes": False,
    }


@given(payload=baseline_scene_payloads())
def test_render_request_generated_payload_validates(payload: dict[str, object]) -> None:
    request = FloorPlanRenderRequest.model_validate(payload)

    assert request.scene is not None
    assert request.scene.scene_level == "baseline"


@given(payload=baseline_scene_payloads())
@settings(max_examples=8, deadline=None)
def test_render_floor_plan_smoke_generated_payload(payload: dict[str, object]) -> None:
    request = FloorPlanRenderRequest.model_validate(payload)
    out_dir = Path("artifacts/test_floor_planner_hypothesis")

    _scene, output, _tool_return = render_floor_plan(
        request,
        scene_revision=1,
        current_scene=None,
        output_dir=out_dir,
    )

    assert Path(output.output_png_path).exists()
    assert Path(output.output_svg_path).exists()
