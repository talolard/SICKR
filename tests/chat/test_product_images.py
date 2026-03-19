from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from ikea_agent.chat.product_images import (
    build_catalog_image_url,
    build_primary_image_url,
    build_ranked_image_url,
    product_id_from_canonical_key,
)
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app


def test_build_catalog_image_url_prefers_proxy_routes_for_backend_serving() -> None:
    assert (
        build_catalog_image_url(
            product_id="28508",
            ordinal=1,
            public_url="https://example.test/primary.jpg",
            serving_strategy="backend_proxy",
            base_url=None,
        )
        == "/static/product-images/28508"
    )
    assert (
        build_catalog_image_url(
            product_id="28508",
            ordinal=2,
            public_url="https://example.test/secondary.jpg",
            serving_strategy="backend_proxy",
            base_url="https://app.example.test",
        )
        == "https://app.example.test/static/product-images/28508/2"
    )


def test_build_catalog_image_url_can_pass_through_public_urls() -> None:
    assert (
        build_catalog_image_url(
            product_id="348326",
            ordinal=1,
            public_url="https://example.test/gamma.jpg",
            serving_strategy="direct_public_url",
            base_url=None,
        )
        == "https://example.test/gamma.jpg"
    )


def test_build_primary_and_ranked_image_urls_use_stable_routes() -> None:
    assert build_primary_image_url(product_id="90458891") == "/static/product-images/90458891"
    assert build_ranked_image_url(product_id="90458891", ordinal=3) == (
        "/static/product-images/90458891/3"
    )


def test_product_id_from_canonical_key_splits_country_suffix() -> None:
    assert product_id_from_canonical_key("28508-DE") == "28508"
    assert product_id_from_canonical_key("90606797-SE") == "90606797"
    assert product_id_from_canonical_key("product-without-country") == "product-without-country"


@dataclass(frozen=True, slots=True)
class _CatalogRepositoryStub:
    image_path: Path

    def resolve_product_image_path(
        self,
        *,
        product_id: str,
        ordinal: int | None = None,
    ) -> Path | None:
        if product_id != "90458891":
            return None
        target_ordinal = 1 if ordinal is None else ordinal
        if target_ordinal != 1:
            return None
        return self.image_path


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    catalog_repository: _CatalogRepositoryStub


def test_create_app_serves_product_images_from_catalog_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "served.jpg"
    image_path.write_bytes(b"served-image")

    monkeypatch.setattr("ikea_agent.chat_app.main.list_agent_catalog", list)

    client = TestClient(
        create_app(
            runtime=cast(
                "ChatRuntime",
                _RuntimeStub(catalog_repository=_CatalogRepositoryStub(image_path=image_path)),
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
