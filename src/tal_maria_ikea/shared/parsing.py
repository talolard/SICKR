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


def parse_dimensions_text(dimensions_text: str | None) -> ParsedDimensions:
    """Extract the first three numeric tokens from a dimensions string.

    IKEA measurements vary by locale and format. For Phase 1 we use a tolerant,
    deterministic parser: first token -> width, second -> depth, third -> height.
    """

    if not dimensions_text:
        return ParsedDimensions(width_cm=None, depth_cm=None, height_cm=None)

    tokens = _DIMENSION_TOKEN_RE.findall(dimensions_text)
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
