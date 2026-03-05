from __future__ import annotations

import pytest
from pydantic import ValidationError

from ikea_agent.tools.floorplanner.models import FloorPlanRequest


def _valid_payload() -> dict[str, object]:
    return {
        "elements": [
            {
                "type": "wall",
                "name": "south_wall",
                "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                "length_cm": 340.0,
            },
            {
                "type": "wall",
                "name": "east_wall",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 0.0},
                "length_cm": 260.0,
                "orientation_angle_deg": 90.0,
            },
            {
                "type": "wall",
                "name": "north_wall",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 260.0},
                "length_cm": 340.0,
                "orientation_angle_deg": 180.0,
            },
            {
                "type": "door",
                "name": "entry_door",
                "anchor_point_cm": {"x_cm": 10.0, "y_cm": 0.0},
                "to_the_right": True,
            },
            {
                "type": "window",
                "name": "right_window",
                "anchor_point_cm": {"x_cm": 340.0, "y_cm": 30.0},
                "orientation_angle_deg": 90.0,
            },
        ],
    }


def test_floor_plan_request_accepts_valid_payload() -> None:
    request = FloorPlanRequest.model_validate(_valid_payload())

    assert request.count_elements("wall") == 3
    assert request.count_elements("door") == 1
    assert request.count_elements("window") == 1


def test_to_renovation_settings_uses_meter_units() -> None:
    request = FloorPlanRequest.model_validate(_valid_payload())

    settings = request.to_renovation_settings("artifacts/floor_plans")
    layout = settings["default_layout"]
    elements = settings["floor_plans"][0]["elements"]  # type: ignore[index]

    assert layout["top_right_corner"] == pytest.approx((3.9, 3.1))  # type: ignore[index]
    assert layout["grid_major_step"] == 0.5  # type: ignore[index]
    wall = elements[0]
    assert wall["type"] == "wall"
    assert wall["length"] == 3.4
    assert wall["thickness"] == 0.1


def test_to_renovation_settings_is_idempotent() -> None:
    request = FloorPlanRequest.model_validate(_valid_payload())
    before = request.model_dump()

    _ = request.to_renovation_settings("artifacts/floor_plans")

    assert request.model_dump() == before


def test_floor_plan_request_schema_is_agent_friendly() -> None:
    schema = FloorPlanRequest.model_json_schema()
    element_schema = schema["properties"]["elements"]
    include_image_schema = schema["properties"]["include_image_bytes"]

    assert "description" in element_schema
    assert "at least three walls" in element_schema["description"].lower()
    assert include_image_schema["type"] == "boolean"
    assert "binary content" in include_image_schema["description"].lower()
    assert "examples" in schema


@pytest.mark.parametrize(
    ("mutator", "expected_message"),
    [
        (
            lambda payload: payload["elements"].append(  # type: ignore[index]
                {
                    "type": "door",
                    "name": "too_wide_door",
                    "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "doorway_width_cm": 70.0,
                    "door_width_cm": 80.0,
                    "thickness_cm": 5.0,
                }
            ),
            "door_width_cm must be less than or equal to doorway_width_cm",
        ),
        (
            lambda payload: payload["elements"].append(  # type: ignore[index]
                {
                    "type": "window",
                    "name": "bad_window",
                    "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "length_cm": 100.0,
                    "overall_thickness_cm": 6.0,
                    "single_line_thickness_cm": 3.0,
                }
            ),
            "single_line_thickness_cm must be less than half",
        ),
        (
            lambda payload: payload.update(
                {
                    "elements": [
                        {
                            "type": "door",
                            "name": "only_door",
                            "anchor_point_cm": {"x_cm": 10.0, "y_cm": 0.0},
                            "doorway_width_cm": 90.0,
                            "door_width_cm": 80.0,
                            "thickness_cm": 5.0,
                        }
                    ]
                }
            ),
            "At least three wall elements are required",
        ),
        (
            lambda payload: payload["elements"].append(  # type: ignore[index]
                {
                    "type": "wall",
                    "name": "south_wall",
                    "anchor_point_cm": {"x_cm": 0.0, "y_cm": 0.0},
                    "length_cm": 200.0,
                }
            ),
            "Element names must be unique",
        ),
    ],
)
def test_floor_plan_request_rejects_invalid_payloads(
    mutator: object,
    expected_message: str,
) -> None:
    payload = _valid_payload()
    mutator(payload)  # type: ignore[operator]

    with pytest.raises(ValidationError, match=expected_message):
        FloorPlanRequest.model_validate(payload)
