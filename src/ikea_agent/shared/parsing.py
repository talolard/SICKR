"""Parsing helpers for numeric filters and free-form dimensions text."""

from __future__ import annotations

import re
from dataclasses import dataclass

_DIMENSION_TOKEN_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_DIMENSION_AXIS_COUNT = 3


@dataclass(frozen=True, slots=True)
class ParsedDimensions:
    """Parsed width/depth/height centimeters from a measurement string."""

    width_cm: float | None
    depth_cm: float | None
    height_cm: float | None


def classify_dimensions_type(dimensions_text: str | None) -> str:
    """Classify raw dimensions string into a known parsing strategy type."""

    if not dimensions_text:
        return "missing"

    normalized = dimensions_text.strip().lower()
    if normalized in {"", "none"}:
        return "missing"

    checks: tuple[tuple[bool, str], ...] = (
        (_matches(normalized, r"^\d+(?:[.,]\d+)?\s*cm$"), "cm_single"),
        (_matches(normalized, r"^\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*cm$"), "cm_double"),
        (
            _matches(
                normalized,
                r"^\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*cm$",
            ),
            "cm_triple",
        ),
        ("(" in normalized and "cm" in normalized, "cm_with_parenthetical"),
        ("/" in normalized and "cm" in normalized, "cm_with_alternatives"),
        ("m²" in normalized and "cm" in normalized, "area_with_height"),
        ("cm" in normalized, "cm_other"),
    )
    for is_match, dimensions_type in checks:
        if is_match:
            return dimensions_type

    return "non_cm_or_unknown"


def parse_dimensions_text(dimensions_text: str | None) -> ParsedDimensions:
    """Extract the first three numeric tokens from a dimensions string.

    IKEA measurements vary by locale and format. For Phase 1 we use a tolerant,
    deterministic parser: first token -> width, second -> depth, third -> height.
    """

    if not dimensions_text:
        return ParsedDimensions(width_cm=None, depth_cm=None, height_cm=None)

    normalized = dimensions_text.lower()
    parse_source = normalized.split("(", maxsplit=1)[0].strip()
    tokens = _DIMENSION_TOKEN_RE.findall(parse_source)
    values = [_to_float(token) for token in tokens[:_DIMENSION_AXIS_COUNT]]
    while len(values) < _DIMENSION_AXIS_COUNT:
        values.append(None)

    return ParsedDimensions(width_cm=values[0], depth_cm=values[1], height_cm=values[2])


def _to_float(value: str) -> float | None:
    """Convert a potentially comma-delimited decimal string to float."""

    normalized = value.replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _matches(text: str, pattern: str) -> bool:
    return re.fullmatch(pattern, text) is not None
