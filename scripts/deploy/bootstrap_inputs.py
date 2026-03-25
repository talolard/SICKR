"""Helpers for the deploy bootstrap input contract.

This module computes the seed versions that deployment automation must pin for
the release manifest and later verify on the host. The calculations intentionally
mirror `scripts/docker_deps/seed_postgres.py`, but they accept virtual container
paths so CI can compute the same fingerprints that the runtime seed step writes
inside the container.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

_POSTGRES_PARQUET_RELATIVE_PATHS = (
    PurePosixPath("data/parquet/products_canonical"),
    PurePosixPath("data/parquet/product_embeddings"),
)
_BACKEND_CONTAINER_REPO_ROOT = PurePosixPath("/app")


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
    postgres_paths = [
        (_BACKEND_CONTAINER_REPO_ROOT / relative_path, repo_root / relative_path)
        for relative_path in _POSTGRES_PARQUET_RELATIVE_PATHS
    ]
    return ReleaseBootstrapInputs(
        postgres_seed_version=fingerprint_virtual_paths(postgres_paths),
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


def fingerprint_virtual_paths(paths: list[tuple[PurePosixPath, Path]]) -> str:
    """Return the seed fingerprint for one ordered set of virtual/actual paths."""

    digest = sha256()
    for virtual_path, actual_path in sorted(paths, key=lambda item: item[0].as_posix()):
        resolved_actual_path = actual_path.expanduser().resolve()
        digest.update(virtual_path.as_posix().encode())
        if resolved_actual_path.is_dir():
            for file_path in sorted(
                item for item in resolved_actual_path.rglob("*") if item.is_file()
            ):
                digest.update(str(file_path.relative_to(resolved_actual_path)).encode())
                stat = file_path.stat()
                digest.update(str(stat.st_size).encode())
                digest.update(str(stat.st_mtime_ns).encode())
        else:
            stat = resolved_actual_path.stat()
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()
