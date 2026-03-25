"""Helpers for the deploy bootstrap input contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.deploy.seed_fingerprint import calculate_postgres_seed_version


@dataclass(frozen=True, slots=True)
class ReleaseBootstrapInputs:
    """Pinned non-secret bootstrap inputs for one deployable release."""

    postgres_seed_version: str
    image_catalog_run_id: str


def create_release_bootstrap_inputs(
    *, repo_root: Path, image_catalog_run_id: str
) -> ReleaseBootstrapInputs:
    """Return the release-bootstrap contract for one checked-out release commit."""

    normalized_run_id = validate_image_catalog_run_id(image_catalog_run_id)
    return ReleaseBootstrapInputs(
        postgres_seed_version=calculate_postgres_seed_version(repo_root=repo_root),
        image_catalog_run_id=normalized_run_id,
    )


def validate_image_catalog_run_id(image_catalog_run_id: str) -> str:
    """Normalize and validate one deploy-approved image-catalog run id."""

    normalized = image_catalog_run_id.strip()
    if not normalized:
        msg = "Expected a non-empty IKEA image catalog run id."
        raise ValueError(msg)
    if "/" in normalized or "\\" in normalized:
        msg = (
            "Image catalog run id must be one path segment so deploy automation "
            f"cannot escape the configured bootstrap root: {image_catalog_run_id!r}."
        )
        raise ValueError(msg)
    return normalized
