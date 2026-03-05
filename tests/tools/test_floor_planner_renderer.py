from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tal_maria_ikea.tools.floor_planner_models import FloorPlanRequest
from tal_maria_ikea.tools.floor_planner_renderer import FloorPlannerRenderer

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "floor_planner"


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text())
    if not isinstance(loaded, dict):
        msg = f"Expected mapping at fixture root for {path}"
        raise TypeError(msg)
    return loaded


def test_renderer_writes_png_for_complex_room(tmp_path: Path) -> None:
    payload = _load_yaml(_FIXTURE_DIR / "valid_room_complex.yaml")
    request = FloorPlanRequest.model_validate(payload)

    result = FloorPlannerRenderer().render(request, tmp_path)

    assert result.output_png.exists()
    assert result.output_png.name == "tal_room_recessed.png"
    assert result.output_png.stat().st_size > 0
    assert result.wall_count == 6


def test_renderer_writes_png_for_hallway(tmp_path: Path) -> None:
    payload = _load_yaml(_FIXTURE_DIR / "valid_hallway_7m_x_2_5m.yaml")
    request = FloorPlanRequest.model_validate(payload)

    result = FloorPlannerRenderer().render(request, tmp_path)

    assert result.output_png.exists()
    assert result.output_png.name == "long_hallway.png"
    assert result.output_png.stat().st_size > 0
    assert result.door_count == 4
