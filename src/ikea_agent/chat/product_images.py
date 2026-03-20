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


def build_catalog_image_url(
    *,
    product_id: str,
    ordinal: int,
    public_url: str | None,
    serving_strategy: Literal["backend_proxy", "direct_public_url"],
    base_url: str | None,
) -> str:
    """Return the runtime image URL for one ordered image row."""

    if serving_strategy == "direct_public_url" and public_url:
        return public_url
    if ordinal == _DEFAULT_PRODUCT_IMAGE_ORDINAL:
        return build_primary_image_url(product_id=product_id, base_url=base_url)
    return build_ranked_image_url(product_id=product_id, ordinal=ordinal, base_url=base_url)


def image_sort_key(
    *,
    is_og_image: bool,
    image_rank: int | None,
    stable_key: str,
) -> tuple[int, int, str]:
    """Return a deterministic image ordering key shared by lookup paths."""

    return (
        0 if is_og_image else 1,
        image_rank if image_rank is not None else 2**31 - 1,
        stable_key,
    )


def product_id_from_canonical_key(canonical_product_key: str) -> str:
    """Derive raw IKEA `product_id` from the repo canonical key."""

    head, separator, tail = canonical_product_key.rpartition("-")
    if separator and tail.isalpha() and len(tail) in {2, 3}:
        return head
    return canonical_product_key


def _join_base_url(*, base_url: str | None, path: str) -> str:
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"
