"""Stable seed fingerprint helpers shared by deploy and bootstrap tooling.

The first live deploy exposed that mtime-based fingerprints drift across CI,
local checkouts, and runtime environments. These helpers intentionally hash the
logical path contract plus file contents so the same canonical inputs produce
the same seed version everywhere.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath

_POSTGRES_PARQUET_RELATIVE_PATHS = (
    PurePosixPath("data/parquet/products_canonical"),
    PurePosixPath("data/parquet/product_embeddings"),
)
_BACKEND_CONTAINER_REPO_ROOT = PurePosixPath("/app")
_IMAGE_CATALOG_CONTAINER_ROOT = PurePosixPath("/app/ikea_image_catalog")


def calculate_postgres_seed_version(*, repo_root: Path) -> str:
    """Return the deploy-time seed version for canonical parquet inputs.

    The logical paths intentionally match the backend container filesystem so
    release CI and runtime bootstrap compute the same version string even when
    the checkout or execution root differs.
    """

    return fingerprint_virtual_paths(postgres_seed_virtual_paths(repo_root=repo_root))


def calculate_image_catalog_seed_version(
    *,
    image_catalog_root: Path,
    image_catalog_source: Path,
) -> str:
    """Return the seed version for one selected image-catalog source artifact."""

    resolved_root = image_catalog_root.expanduser().resolve()
    resolved_source = image_catalog_source.expanduser().resolve()
    logical_path = _IMAGE_CATALOG_CONTAINER_ROOT / resolved_source.relative_to(resolved_root)
    return fingerprint_virtual_paths([(logical_path, resolved_source)])


def postgres_seed_virtual_paths(*, repo_root: Path) -> list[tuple[PurePosixPath, Path]]:
    """Return the logical/actual parquet path mapping for postgres seed inputs."""

    resolved_root = repo_root.expanduser().resolve()
    return [
        (_BACKEND_CONTAINER_REPO_ROOT / relative_path, resolved_root / relative_path)
        for relative_path in _POSTGRES_PARQUET_RELATIVE_PATHS
    ]


def fingerprint_virtual_paths(paths: list[tuple[PurePosixPath, Path]]) -> str:
    """Return one stable fingerprint for ordered logical/actual path pairs."""

    digest = sha256()
    for logical_path, actual_path in sorted(paths, key=lambda item: item[0].as_posix()):
        resolved_actual_path = actual_path.expanduser().resolve()
        if resolved_actual_path.is_dir():
            for file_path in sorted(
                item for item in resolved_actual_path.rglob("*") if item.is_file()
            ):
                relative_file_path = file_path.relative_to(resolved_actual_path)
                digest.update((logical_path / relative_file_path).as_posix().encode())
                digest.update(_sha256_for_path(file_path).encode())
        else:
            digest.update(logical_path.as_posix().encode())
            digest.update(_sha256_for_path(resolved_actual_path).encode())
    return digest.hexdigest()


def _sha256_for_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
