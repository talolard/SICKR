from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts.deploy.bootstrap_catalog_from_s3 import main as bootstrap_catalog_from_s3_main
from scripts.docker_deps.seed_postgres import SeedSummary


class StubS3Client:
    def __init__(self) -> None:
        self.downloads: list[tuple[str, str, str]] = []
        self.keys = [
            "bootstrap/demo/product_embeddings",
            "bootstrap/demo/products_canonical/country=Germany/data_0.parquet",
            "bootstrap/demo/catalog.parquet",
        ]

    def get_paginator(self, name: str) -> SimpleNamespace:
        assert name == "list_objects_v2"
        return SimpleNamespace(paginate=self.paginate)

    def paginate(self, **kwargs: str) -> list[dict[str, object]]:
        assert kwargs["Bucket"] == "private-bucket"
        prefix = kwargs["Prefix"]
        return [{"Contents": [{"Key": key} for key in self.keys if key.startswith(prefix)]}]

    def download_file(self, bucket: str, key: str, destination: str) -> None:
        self.downloads.append((bucket, key, destination))
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_text("stub", encoding="utf-8")


def test_bootstrap_catalog_from_s3_downloads_artifacts_and_prints_summary(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s3_client = StubS3Client()
    captured_kwargs: dict[str, object] = {}

    def fake_boto3_client(service_name: str, region_name: str | None = None) -> StubS3Client:
        assert service_name == "s3"
        assert region_name == "eu-central-1"
        return s3_client

    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.get_settings",
        lambda: SimpleNamespace(
            log_level="INFO",
            log_json=True,
            database_url="sqlite:///ignored.sqlite3",
            database_pool_mode="nullpool",
            artifact_s3_region="eu-central-1",
            release_version="1.2.3",
        ),
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.configure_logging", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.configure_logfire", lambda _settings: None
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.resolve_database_url",
        lambda *, database_url: database_url,
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.create_database_engine",
        lambda _database_url, pool_mode: {"pool_mode": pool_mode},
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.boto3.client",
        fake_boto3_client,
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog_from_s3.seed_postgres_database",
        lambda **kwargs: (
            captured_kwargs.update(kwargs)
            or SeedSummary(
                postgres_seed_version="seed-v1",
                image_catalog_seed_version="image-v1",
                image_catalog_source="catalog.parquet",
                products_count=1,
                embeddings_count=1,
                image_count=1,
                skipped=False,
            )
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap_catalog_from_s3.py",
            "--artifacts-bucket",
            "private-bucket",
            "--artifacts-prefix",
            "bootstrap/demo",
            "--image-catalog-object-name",
            "catalog.parquet",
            "--image-catalog-run-id",
            "germany-all-products-20260318",
            "--product-image-base-url",
            "https://designagent.talperry.com/static/product-images",
        ],
    )

    bootstrap_catalog_from_s3_main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["products_count"] == 1
    assert captured_kwargs["product_image_base_url"] == (
        "https://designagent.talperry.com/static/product-images"
    )
    repo_root = captured_kwargs["repo_root"]
    image_catalog_root = captured_kwargs["image_catalog_root"]
    assert isinstance(repo_root, Path)
    assert isinstance(image_catalog_root, Path)
    assert s3_client.downloads == [
        (
            "private-bucket",
            "bootstrap/demo/product_embeddings",
            str(repo_root / "data" / "parquet" / "product_embeddings"),
        ),
        (
            "private-bucket",
            "bootstrap/demo/products_canonical/country=Germany/data_0.parquet",
            str(
                repo_root
                / "data"
                / "parquet"
                / "products_canonical"
                / "country=Germany"
                / "data_0.parquet"
            ),
        ),
        (
            "private-bucket",
            "bootstrap/demo/catalog.parquet",
            str(image_catalog_root / "runs" / "germany-all-products-20260318" / "catalog.parquet"),
        ),
    ]
