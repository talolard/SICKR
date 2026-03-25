from __future__ import annotations

from scripts.docker_deps.seed_postgres import _resolve_seed_public_url


def test_resolve_seed_public_url_prefers_same_host_deployment_path() -> None:
    public_url = _resolve_seed_public_url(
        image_asset_key="10018194-primary.jpg",
        product_image_base_url="https://designagent.talperry.com/static/product-images",
    )

    assert (
        public_url
        == "https://designagent.talperry.com/static/product-images/masters/10018194-primary.jpg"
    )


def test_resolve_seed_public_url_requires_same_host_base_url() -> None:
    public_url = _resolve_seed_public_url(
        image_asset_key="10018194-primary.jpg",
        product_image_base_url=None,
    )

    assert public_url is None
