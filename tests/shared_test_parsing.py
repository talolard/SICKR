from __future__ import annotations

from tal_maria_ikea.shared.parsing import parse_dimensions_text


def test_parse_dimensions_text_returns_three_axes() -> None:
    parsed = parse_dimensions_text("120x60x75 cm")

    assert parsed.width_cm == 120.0
    assert parsed.depth_cm == 60.0
    assert parsed.height_cm == 75.0


def test_parse_dimensions_text_handles_partial_input() -> None:
    parsed = parse_dimensions_text("90 cm")

    assert parsed.width_cm == 90.0
    assert parsed.depth_cm is None
    assert parsed.height_cm is None


def test_parse_dimensions_text_handles_none() -> None:
    parsed = parse_dimensions_text(None)

    assert parsed.width_cm is None
    assert parsed.depth_cm is None
    assert parsed.height_cm is None
