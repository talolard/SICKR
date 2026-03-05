from __future__ import annotations

import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic_ai import BinaryContent, ToolReturn

from ikea_agent.tools.floorplanner.models import FloorPlanRequest, PointCm, WallElementCm
from ikea_agent.tools.floorplanner.tool import FloorPlannerToolResult, render_floor_plan

AxisAngleDeg = Literal[-90, 0, 90, 180]


def _direction_for_angle(angle_deg: AxisAngleDeg) -> tuple[int, int]:
    match angle_deg:
        case 0:
            return (1, 0)
        case 90:
            return (0, 1)
        case 180:
            return (-1, 0)
        case -90:
            return (0, -1)
    raise AssertionError(f"Unexpected axis-aligned angle: {angle_deg}")


def _axis_angle_for_delta(dx_cm: int, dy_cm: int) -> AxisAngleDeg:
    if dx_cm > 0 and dy_cm == 0:
        return 0
    if dx_cm < 0 and dy_cm == 0:
        return 180
    if dy_cm > 0 and dx_cm == 0:
        return 90
    if dy_cm < 0 and dx_cm == 0:
        return -90
    raise AssertionError(f"Non-axis-aligned delta: dx={dx_cm} dy={dy_cm}")


def _rectangle_vertices(*, width_cm: int, height_cm: int) -> list[tuple[int, int]]:
    return [
        (0, 0),
        (width_cm, 0),
        (width_cm, height_cm),
        (0, height_cm),
        (0, 0),
    ]


def _notch_vertices(
    *,
    width_cm: int,
    height_cm: int,
    notch_dx_cm: int,
    notch_dy_cm: int,
) -> list[tuple[int, int]]:
    return [
        (0, 0),
        (width_cm, 0),
        (width_cm, notch_dy_cm),
        (width_cm - notch_dx_cm, notch_dy_cm),
        (width_cm - notch_dx_cm, height_cm),
        (0, height_cm),
        (0, 0),
    ]


def _walls_from_vertices(
    vertices: list[tuple[int, int]],
) -> tuple[list[dict[str, Any]], list[tuple[int, int, int, AxisAngleDeg]]]:
    walls: list[dict[str, Any]] = []
    wall_specs: list[tuple[int, int, int, AxisAngleDeg]] = []

    for i, ((x1, y1), (x2, y2)) in enumerate(pairwise(vertices)):
        dx = x2 - x1
        dy = y2 - y1
        angle = _axis_angle_for_delta(dx, dy)
        length_cm = abs(dx) + abs(dy)
        walls.append(
            {
                "type": "wall",
                "name": f"wall_{i}",
                "anchor_point_cm": {"x_cm": float(x1), "y_cm": float(y1)},
                "length_cm": float(length_cm),
                "thickness_cm": 10.0,
                "orientation_angle_deg": float(angle),
            }
        )
        wall_specs.append((x1, y1, length_cm, angle))

    return walls, wall_specs


def _draw_openings(
    draw: st.DrawFn,
    *,
    opening_type: Literal["door", "window"],
    count: int,
    wall_specs: list[tuple[int, int, int, AxisAngleDeg]],
) -> list[dict[str, Any]]:
    openings: list[dict[str, Any]] = []
    min_wall_len = 140 if opening_type == "window" else 120
    candidate_wall_indices = [
        i for i, (_, _, length, _) in enumerate(wall_specs) if length >= min_wall_len
    ]
    if not candidate_wall_indices or count <= 0:
        return openings

    for opening_index in range(count):
        wall_idx = draw(st.sampled_from(candidate_wall_indices))
        start_x, start_y, wall_len, angle = wall_specs[wall_idx]
        dir_x, dir_y = _direction_for_angle(angle)

        if opening_type == "door":
            doorway_width_cm = draw(st.integers(min_value=70, max_value=min(120, wall_len - 20)))
            door_width_cm = draw(st.integers(min_value=60, max_value=doorway_width_cm))
            opening_len = doorway_width_cm
            element: dict[str, Any] = {
                "type": "door",
                "name": f"door_{opening_index}",
                "doorway_width_cm": float(doorway_width_cm),
                "door_width_cm": float(door_width_cm),
                "thickness_cm": 5.0,
                "to_the_right": draw(st.booleans()),
            }
        else:
            window_len_cm = draw(st.integers(min_value=60, max_value=min(200, wall_len - 20)))
            opening_len = window_len_cm
            overall_thickness_cm = draw(st.integers(min_value=8, max_value=20))
            single_line_thickness_cm = draw(
                st.integers(min_value=1, max_value=max(1, (overall_thickness_cm // 2) - 1)),
            )
            element = {
                "type": "window",
                "name": f"window_{opening_index}",
                "length_cm": float(window_len_cm),
                "overall_thickness_cm": float(overall_thickness_cm),
                "single_line_thickness_cm": float(single_line_thickness_cm),
            }

        margin = 10
        max_offset = wall_len - opening_len - margin
        if max_offset <= margin:
            continue
        offset = draw(st.integers(min_value=margin, max_value=max_offset))

        element.update(
            {
                "anchor_point_cm": {
                    "x_cm": float(start_x + dir_x * offset),
                    "y_cm": float(start_y + dir_y * offset),
                },
                "orientation_angle_deg": float(angle),
            }
        )
        openings.append(element)

    return openings


@st.composite
def floor_plan_payloads(draw: st.DrawFn) -> dict[str, Any]:
    """Generate plausibly viable room layouts for FloorPlanRequest.

    Strategy goals:
    - axis-aligned walls that form a closed boundary (rectangle or a single-notch concave room)
    - occasional doors/windows anchored to random walls, with sizes/offsets that keep them on-wall
    """

    width_cm = draw(st.integers(min_value=200, max_value=900))
    height_cm = draw(st.integers(min_value=200, max_value=900))
    kind_roll = draw(st.integers(min_value=0, max_value=9))

    if kind_roll < 3:
        notch_dx_cm = draw(st.integers(min_value=50, max_value=width_cm - 50))
        notch_dy_cm = draw(st.integers(min_value=50, max_value=height_cm - 50))
        vertices = _notch_vertices(
            width_cm=width_cm,
            height_cm=height_cm,
            notch_dx_cm=notch_dx_cm,
            notch_dy_cm=notch_dy_cm,
        )
    else:
        vertices = _rectangle_vertices(width_cm=width_cm, height_cm=height_cm)

    walls, wall_specs = _walls_from_vertices(vertices)
    door_count = draw(st.integers(min_value=0, max_value=2))
    window_count = draw(st.integers(min_value=0, max_value=2))
    doors = _draw_openings(draw, opening_type="door", count=door_count, wall_specs=wall_specs)
    windows = _draw_openings(draw, opening_type="window", count=window_count, wall_specs=wall_specs)

    elements = [*walls, *doors, *windows]
    layout_padding_cm = draw(
        st.floats(
            min_value=0.0,
            max_value=150.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )

    return {
        "elements": elements,
        "layout_padding_cm": layout_padding_cm,
        "include_image_bytes": False,
    }


@given(payload=floor_plan_payloads())
@settings(max_examples=50)
def test_floor_plan_request_generated_payload_round_trips_to_settings(
    payload: dict[str, Any],
) -> None:
    request = FloorPlanRequest.model_validate(payload)
    before = request.model_dump()

    settings_dict = request.to_renovation_settings("artifacts/floor_plans")

    assert request.model_dump() == before
    assert "default_layout" in settings_dict
    assert "project" in settings_dict
    assert "floor_plans" in settings_dict

    assert request.count_elements("wall") >= 3
    assert request.count_elements("door") == sum(1 for e in request.elements if e.type == "door")
    assert request.count_elements("window") == sum(
        1 for e in request.elements if e.type == "window"
    )

    layout = settings_dict["default_layout"]
    bottom_left = layout["bottom_left_corner"]  # type: ignore[index]
    top_right = layout["top_right_corner"]  # type: ignore[index]
    assert bottom_left[0] < top_right[0]
    assert bottom_left[1] < top_right[1]

    points_cm: list[PointCm] = []
    for element in request.elements:
        points_cm.extend(element.extent_points_cm())

    eps = 1e-9
    for point in points_cm:
        x_m, y_m = point.to_meters_tuple()
        assert bottom_left[0] - eps <= x_m <= top_right[0] + eps
        assert bottom_left[1] - eps <= y_m <= top_right[1] + eps

    # Unit conversion sanity: at least one wall and thickness/length are in meters.
    first_wall = next(e for e in request.elements if isinstance(e, WallElementCm))
    rendered_wall = settings_dict["floor_plans"][0]["elements"][0]  # type: ignore[index]
    assert rendered_wall["type"] == "wall"
    assert rendered_wall["length"] == pytest.approx(first_wall.length_cm / 100.0)
    assert rendered_wall["thickness"] == pytest.approx(first_wall.thickness_cm / 100.0)


@given(payload=floor_plan_payloads())
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_render_floor_plan_smoke_generated_payload(payload: dict[str, Any]) -> None:
    request = FloorPlanRequest.model_validate(payload)

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir)
        result = render_floor_plan(request, output_dir=out_dir)

        assert isinstance(result, FloorPlannerToolResult)
        assert Path(result.output_png_path).exists()
        assert Path(result.output_png_path).stat().st_size > 0
        assert result.wall_count == request.count_elements("wall")
        assert result.door_count == request.count_elements("door")
        assert result.window_count == request.count_elements("window")


@given(payload=floor_plan_payloads())
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_render_floor_plan_smoke_generated_payload_returns_tool_return(
    payload: dict[str, Any],
) -> None:
    request = FloorPlanRequest.model_validate(payload).model_copy(
        update={"include_image_bytes": True}
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir)
        result = render_floor_plan(request, output_dir=out_dir)

        assert isinstance(result, ToolReturn)
        assert result.metadata is not None
        assert result.metadata["wall_count"] == request.count_elements("wall")
        assert result.metadata["door_count"] == request.count_elements("door")
        assert result.metadata["window_count"] == request.count_elements("window")
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], BinaryContent)
        assert result.content[0].media_type == "image/png"
        assert len(result.content[0].data) > 0
