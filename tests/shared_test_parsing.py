from __future__ import annotations

from ikea_agent.shared.parsing import classify_dimensions_type, parse_dimensions_text


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


def test_classify_dimensions_type_core_patterns() -> None:
    assert classify_dimensions_type("120 cm") == "cm_single"
    assert classify_dimensions_type("120x60 cm") == "cm_double"
    assert classify_dimensions_type("120x60x75 cm") == "cm_triple"


def test_classify_dimensions_type_parenthetical_and_alternative() -> None:
    assert (
        classify_dimensions_type('50x27x36 cm (19 5/8x10 5/8x14 1/8 ")') == "cm_with_parenthetical"
    )
    assert classify_dimensions_type("140x200/80x80 cm") == "cm_with_alternatives"


def test_parse_dimensions_text_strips_parenthetical_imperial_suffix() -> None:
    parsed = parse_dimensions_text('50x27x36 cm (19 5/8x10 5/8x14 1/8 ")')
    assert parsed.width_cm == 50.0
    assert parsed.depth_cm == 27.0
    assert parsed.height_cm == 36.0
