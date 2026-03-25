"""Helpers for product-image URL routing and ordering."""

from __future__ import annotations

from typing import Literal

_DEFAULT_PRODUCT_IMAGE_ORDINAL = 1


def build_primary_image_url(*, product_id: str, base_url: str | None = None) -> str:
    """Return the stable route for a product's primary image."""

    return _join_base_url(base_url=base_url, path=f"/static/product-images/{product_id}")


def build_ranked_image_url(*, product_id: str, ordinal: int, base_url: str | None = None) -> str:
    """Return the stable route for a product image at a given 1-based ordinal."""

    return _join_base_url(
        base_url=base_url,
        path=f"/static/product-images/{product_id}/{ordinal}",
    )


def build_seeded_public_image_url(
    *,
    base_url: str,
    image_asset_key: str,
) -> str:
    """Return the deterministic same-host public URL used for deployed image seeding."""

    return _join_base_url(base_url=base_url, path=f"/masters/{image_asset_key}")


def build_catalog_image_url(
    *,
    product_id: str,
    ordinal: int,
    public_url: str | None,
    serving_strategy: Literal["backend_proxy", "direct_public_url"],
    base_url: str | None,
) -> str:
    """Return the runtime image URL for one ordered image row."""

    if serving_strategy == "direct_public_url":
        return _require_direct_public_image_url(public_url=public_url, base_url=base_url)
    if ordinal == _DEFAULT_PRODUCT_IMAGE_ORDINAL:
        return build_primary_image_url(product_id=product_id, base_url=base_url)
    return build_ranked_image_url(product_id=product_id, ordinal=ordinal, base_url=base_url)


def _join_base_url(*, base_url: str | None, path: str) -> str:
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"


def _require_direct_public_image_url(*, public_url: str | None, base_url: str | None) -> str:
    if not public_url:
        msg = (
            "direct_public_url mode requires seeded catalog.product_images.public_url values. "
            "Bootstrap must populate same-host image URLs before this mode is enabled."
        )
        raise ValueError(msg)
    if base_url:
        normalized_prefix = f"{base_url.rstrip('/')}/"
        if not public_url.startswith(normalized_prefix):
            msg = (
                "direct_public_url mode requires seeded same-host product image URLs "
                f"under {normalized_prefix}."
            )
            raise ValueError(msg)
    return public_url
