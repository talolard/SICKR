from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import parquet as pq

from ikea_agent.chat.product_images import (
    IndexedProductImage,
    ProductImageCatalog,
    product_id_from_canonical_key,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app


def _write_catalog_jsonl(
    *,
    root: Path,
    run_id: str,
    rows: list[dict[str, object]],
) -> Path:
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    catalog_path = run_dir / "catalog.jsonl"
    catalog_path.write_text(
        "\n".join(json.dumps(row) for row in rows),
        encoding="utf-8",
    )
    return catalog_path


def _write_catalog_parquet(
    *,
    root: Path,
    run_id: str,
    rows: list[dict[str, object]],
) -> Path:
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    parquet_path = run_dir / "catalog.parquet"
    pq.write_table(pa.Table.from_pylist(rows), parquet_path)
    return parquet_path


def test_product_image_catalog_indexes_ranked_images_from_jsonl(tmp_path: Path) -> None:
    image_root = tmp_path / "images"
    image_root.mkdir()
    primary = image_root / "alpha.jpg"
    primary.write_bytes(b"alpha")
    secondary = image_root / "beta.jpg"
    secondary.write_bytes(b"beta")
    missing = image_root / "missing.jpg"

    _write_catalog_jsonl(
        root=tmp_path,
        run_id="run-1",
        rows=[
            {
                "product_id": "28508",
                "local_path": str(secondary),
                "image_rank": 2,
                "is_og_image": False,
                "canonical_image_url": "https://example.test/secondary.jpg",
            },
            {
                "product_id": "28508",
                "local_path": str(primary),
                "image_rank": 5,
                "is_og_image": True,
                "canonical_image_url": "https://example.test/primary.jpg",
            },
            {
                "product_id": "28508",
                "local_path": str(missing),
                "image_rank": 1,
                "is_og_image": True,
                "canonical_image_url": "https://example.test/missing.jpg",
            },
        ],
    )

    catalog = ProductImageCatalog.from_output_root(output_root=tmp_path)

    assert catalog.image_urls_for_canonical_key(canonical_product_key="28508-DE") == (
        "/static/product-images/28508",
        "/static/product-images/28508/2",
    )
    assert catalog.resolve_image_path(product_id="28508") == primary.resolve()
    assert catalog.resolve_image_path(product_id="28508", ordinal=2) == secondary.resolve()


def test_product_image_catalog_prefers_parquet_when_available(tmp_path: Path) -> None:
    image_root = tmp_path / "images"
    image_root.mkdir()
    image_path = image_root / "gamma.jpg"
    image_path.write_bytes(b"gamma")

    _write_catalog_parquet(
        root=tmp_path,
        run_id="run-2",
        rows=[
            {
                "product_id": "348326",
                "local_path": str(image_path),
                "image_rank": 1,
                "is_og_image": True,
                "canonical_image_url": "https://example.test/gamma.jpg",
            }
        ],
    )

    catalog = ProductImageCatalog.from_output_root(output_root=tmp_path)

    assert catalog.resolve_image_path(product_id="348326") == image_path.resolve()


def test_product_id_from_canonical_key_splits_country_suffix() -> None:
    assert product_id_from_canonical_key("28508-DE") == "28508"
    assert product_id_from_canonical_key("90606797-SE") == "90606797"
    assert product_id_from_canonical_key("product-without-country") == "product-without-country"


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    product_image_catalog: ProductImageCatalog


def test_create_app_serves_indexed_product_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "served.jpg"
    image_path.write_bytes(b"served-image")
    catalog = ProductImageCatalog(
        output_root=tmp_path,
        images_by_product_id={
            "90458891": (
                IndexedProductImage(
                    product_id="90458891",
                    local_path=image_path.resolve(),
                    image_rank=1,
                    is_og_image=True,
                    public_url=None,
                    storage_backend_kind="local_shared_root",
                ),
            )
        },
    )

    monkeypatch.setattr("ikea_agent.chat_app.main.list_agent_catalog", list)

    client = TestClient(
        create_app(
            runtime=cast(
                "ChatRuntime",
                _RuntimeStub(product_image_catalog=catalog),
            ),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    primary_response = client.get("/static/product-images/90458891")
    ranked_response = client.get("/static/product-images/90458891/1")
    missing_response = client.get("/static/product-images/90458891/2")

    assert primary_response.status_code == 200
    assert primary_response.content == b"served-image"
    assert ranked_response.status_code == 200
    assert missing_response.status_code == 404
