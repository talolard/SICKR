"""ORM models for catalog-side runtime tables queried directly by the app."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped

from ikea_agent.retrieval.schema import product_images


class CatalogBase(DeclarativeBase):
    """Separate declarative base for read-only catalog-side runtime models."""


class ProductImageRecord(CatalogBase):
    """Seeded product-image metadata used by runtime lookup paths."""

    __table__ = product_images

    image_asset_key: Mapped[str]
    canonical_product_key: Mapped[str]
    product_id: Mapped[str]
    image_rank: Mapped[int | None]
    is_og_image: Mapped[bool]
    image_role: Mapped[str | None]
    storage_backend_kind: Mapped[str]
    storage_locator: Mapped[str]
    public_url: Mapped[str | None]
    local_path: Mapped[str | None]
    canonical_image_url: Mapped[str | None]
    provenance: Mapped[str | None]
    crawl_run_id: Mapped[str | None]
    source_page_url: Mapped[str | None]
    sha256: Mapped[str | None]
    content_type: Mapped[str | None]
    width_px: Mapped[int | None]
    height_px: Mapped[int | None]
    refreshed_at: Mapped[datetime | None]
