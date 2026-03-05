from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tal_maria_ikea.tools.floor_planner_models import FloorPlanRequest

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "floor_planner"


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text())
    if not isinstance(loaded, dict):
        msg = f"Expected mapping at fixture root for {path}"
        raise TypeError(msg)
    return loaded


@pytest.mark.parametrize(
    "fixture_name",
    ["valid_room_complex.yaml", "valid_hallway_7m_x_2_5m.yaml"],
)
def test_floor_plan_request_accepts_valid_fixture(fixture_name: str) -> None:
    payload = _load_yaml(_FIXTURE_DIR / fixture_name)

    request = FloorPlanRequest.model_validate(payload)

    assert request.plan_name != ""
    assert len(request.walls) >= 4


def test_to_renovation_settings_contains_expected_top_level_keys(tmp_path: Path) -> None:
    payload = _load_yaml(_FIXTURE_DIR / "valid_room_complex.yaml")
    request = FloorPlanRequest.model_validate(payload)

    settings = request.to_renovation_settings(str(tmp_path))

    assert set(settings.keys()) == {
        "project",
        "default_layout",
        "reusable_elements",
        "floor_plans",
    }


@pytest.mark.parametrize(
    ("fixture_name", "expected_message"),
    [
        ("invalid_self_intersecting_boundary.yaml", "intersect"),
        ("invalid_window_outside_wall.yaml", "exceeds wall length"),
        ("invalid_negative_dimension.yaml", "greater than 0"),
        ("invalid_open_polygon.yaml", "closed ordered perimeter"),
    ],
)
def test_floor_plan_request_rejects_invalid_fixture(
    fixture_name: str,
    expected_message: str,
) -> None:
    payload = _load_yaml(_FIXTURE_DIR / fixture_name)

    with pytest.raises(ValidationError, match=expected_message):
        FloorPlanRequest.model_validate(payload)
