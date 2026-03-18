"""Shared coverage surface definitions and staged thresholds.

This file is the single repo-tracked source of truth for local and CI coverage
gates. The current values represent stage A of the ratchet plan: absolute
floors close to current reality plus 100% execution for unit-test code.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase


@dataclass(frozen=True, slots=True)
class CoverageSurfaceConfig:
    """Coverage surface metadata shared by local and CI coverage scripts."""

    key: str
    label: str
    threshold_percent: float
    include_globs: tuple[str, ...]
    compare_to_baseline: bool


BACKEND_SOURCE = CoverageSurfaceConfig(
    key="backend_source",
    label="Backend source",
    threshold_percent=78.0,
    include_globs=("src/ikea_agent/*.py", "src/ikea_agent/**/*.py"),
    compare_to_baseline=True,
)

BACKEND_TESTS = CoverageSurfaceConfig(
    key="backend_tests",
    label="Backend tests",
    threshold_percent=100.0,
    include_globs=("tests/*.py", "tests/**/*.py"),
    compare_to_baseline=True,
)

FRONTEND_SOURCE = CoverageSurfaceConfig(
    key="frontend_source",
    label="Frontend source",
    threshold_percent=37.0,
    include_globs=("ui/src/*.ts", "ui/src/*.tsx", "ui/src/**/*.ts", "ui/src/**/*.tsx"),
    compare_to_baseline=True,
)

FRONTEND_TESTS = CoverageSurfaceConfig(
    key="frontend_tests",
    label="Frontend tests",
    threshold_percent=100.0,
    include_globs=(
        "ui/src/**/*.test.ts",
        "ui/src/**/*.test.tsx",
        "ui/src/test/*.ts",
        "ui/src/test/*.tsx",
        "ui/src/test/**/*.ts",
        "ui/src/test/**/*.tsx",
    ),
    compare_to_baseline=True,
)

SURFACES: tuple[CoverageSurfaceConfig, ...] = (
    BACKEND_SOURCE,
    BACKEND_TESTS,
    FRONTEND_SOURCE,
    FRONTEND_TESTS,
)
SURFACE_BY_KEY = {surface.key: surface for surface in SURFACES}


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def classify_backend_path(path: str) -> str | None:
    """Return the backend coverage surface key for one normalized path."""

    if _matches_any(path, BACKEND_TESTS.include_globs):
        return BACKEND_TESTS.key
    if _matches_any(path, BACKEND_SOURCE.include_globs):
        return BACKEND_SOURCE.key
    return None


def classify_frontend_path(path: str) -> str | None:
    """Return the frontend coverage surface key for one normalized path."""

    if _matches_any(path, FRONTEND_TESTS.include_globs):
        return FRONTEND_TESTS.key
    if _matches_any(path, FRONTEND_SOURCE.include_globs):
        return FRONTEND_SOURCE.key
    return None
