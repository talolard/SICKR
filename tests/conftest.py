"""Shared pytest fixtures for deterministic, no-secrets test execution.

CI and local tests should not accidentally make paid model requests. This
fixture applies Pydantic AI's request gate globally so test failures surface
immediately if a test path tries to hit a live model backend.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic_ai.models import override_allow_model_requests


@pytest.fixture(autouse=True)
def _disable_live_model_requests() -> Iterator[None]:
    """Disable outbound model calls for every test by default."""

    with override_allow_model_requests(False):
        yield
