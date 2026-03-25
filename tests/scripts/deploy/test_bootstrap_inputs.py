from __future__ import annotations

from pathlib import Path

from scripts.deploy.bootstrap_inputs import create_release_bootstrap_inputs
from scripts.deploy.seed_fingerprint import calculate_postgres_seed_version


def _write_parquet_fixture(repo_root: Path, relative_path: str, payload: bytes) -> None:
    target = repo_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def _repo_fixture(repo_root: Path) -> None:
    _write_parquet_fixture(
        repo_root,
        "data/parquet/products_canonical/part-000.parquet",
        b"products-v1",
    )
    _write_parquet_fixture(
        repo_root,
        "data/parquet/product_embeddings/part-000.parquet",
        b"embeddings-v1",
    )


def test_release_bootstrap_inputs_ignore_checkout_path_and_mtime(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "nested" / "repo-b"
    _repo_fixture(repo_a)
    _repo_fixture(repo_b)

    first_file = repo_a / "data/parquet/products_canonical/part-000.parquet"
    second_file = repo_b / "data/parquet/products_canonical/part-000.parquet"
    first_file.touch()
    second_file.touch()

    inputs_a = create_release_bootstrap_inputs(
        repo_root=repo_a,
        image_catalog_run_id="germany-all-products-20260318",
    )
    inputs_b = create_release_bootstrap_inputs(
        repo_root=repo_b,
        image_catalog_run_id="germany-all-products-20260318",
    )

    assert inputs_a.postgres_seed_version == inputs_b.postgres_seed_version


def test_release_bootstrap_inputs_match_seed_runtime_version(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _repo_fixture(repo_root)

    inputs = create_release_bootstrap_inputs(
        repo_root=repo_root,
        image_catalog_run_id="germany-all-products-20260318",
    )

    assert inputs.postgres_seed_version == calculate_postgres_seed_version(repo_root=repo_root)
