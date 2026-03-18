"""Local product image catalog lookup for search and bundle rendering.

The sidecar writes image catalogs under a shared `.tmp_untracked` root outside
the worktree. This module loads completed catalog outputs, ranks the available
local files per product, and exposes stable FastAPI-served URLs for the UI.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Protocol, cast

import duckdb

logger = getLogger(__name__)

_DEFAULT_PRODUCT_IMAGE_ORDINAL = 1


@dataclass(frozen=True, slots=True)
class IndexedProductImage:
    """One local image file ranked for a raw IKEA product id."""

    product_id: str
    local_path: Path
    image_rank: int | None
    is_og_image: bool
    canonical_image_url: str | None


class ProductImageLookup(Protocol):
    """Minimal image lookup surface used by runtime helpers and routes."""

    def image_urls_for_canonical_key(self, *, canonical_product_key: str) -> tuple[str, ...]:
        """Return FastAPI-served URLs for one canonical product key."""

    def resolve_image_path(self, *, product_id: str, ordinal: int | None = None) -> Path | None:
        """Return one local image path for a product and optional ordinal."""


@dataclass(frozen=True, slots=True)
class ProductImageCatalog:
    """In-memory index of local product images keyed by raw `product_id`."""

    output_root: Path
    images_by_product_id: dict[str, tuple[IndexedProductImage, ...]]

    @classmethod
    def empty(cls, *, output_root: Path) -> ProductImageCatalog:
        """Return an empty index rooted at the configured catalog directory."""

        return cls(output_root=output_root, images_by_product_id={})

    @classmethod
    def from_output_root(cls, *, output_root: Path) -> ProductImageCatalog:
        """Build an index from completed sidecar run outputs under one root."""

        run_catalog_paths = _discover_catalog_paths(output_root=output_root)
        if not run_catalog_paths:
            logger.info(
                "product_image_catalog_empty",
                extra={"output_root": str(output_root)},
            )
            return cls.empty(output_root=output_root)

        images_by_product_id: dict[str, dict[Path, IndexedProductImage]] = defaultdict(dict)
        indexed_row_count = 0
        for catalog_path in run_catalog_paths:
            for indexed_image in _load_indexed_images(catalog_path=catalog_path):
                current = images_by_product_id[indexed_image.product_id].get(
                    indexed_image.local_path
                )
                if current is None or _image_sort_key(indexed_image) < _image_sort_key(current):
                    images_by_product_id[indexed_image.product_id][indexed_image.local_path] = (
                        indexed_image
                    )
                indexed_row_count += 1

        finalized: dict[str, tuple[IndexedProductImage, ...]] = {}
        for product_id, images_by_path in images_by_product_id.items():
            finalized[product_id] = tuple(sorted(images_by_path.values(), key=_image_sort_key))

        logger.info(
            "product_image_catalog_indexed",
            extra={
                "output_root": str(output_root),
                "run_catalog_count": len(run_catalog_paths),
                "product_count": len(finalized),
                "indexed_row_count": indexed_row_count,
            },
        )
        return cls(output_root=output_root, images_by_product_id=finalized)

    def image_urls_for_canonical_key(self, *, canonical_product_key: str) -> tuple[str, ...]:
        """Return served image URLs for one canonical product key."""

        return self.image_urls_for_product_id(
            product_id=product_id_from_canonical_key(canonical_product_key)
        )

    def image_urls_for_product_id(self, *, product_id: str) -> tuple[str, ...]:
        """Return served image URLs for one raw IKEA product id."""

        indexed_images = self.images_by_product_id.get(product_id, ())
        if not indexed_images:
            return ()
        urls = [build_primary_image_url(product_id=product_id)]
        urls.extend(
            build_ranked_image_url(product_id=product_id, ordinal=ordinal)
            for ordinal in range(2, len(indexed_images) + 1)
        )
        return tuple(urls)

    def resolve_image_path(self, *, product_id: str, ordinal: int | None = None) -> Path | None:
        """Resolve one local file path for a product and optional 1-based ordinal."""

        indexed_images = self.images_by_product_id.get(product_id, ())
        if not indexed_images:
            return None
        target_ordinal = _DEFAULT_PRODUCT_IMAGE_ORDINAL if ordinal is None else ordinal
        if target_ordinal < 1 or target_ordinal > len(indexed_images):
            return None
        return indexed_images[target_ordinal - 1].local_path


def build_primary_image_url(*, product_id: str) -> str:
    """Return the stable route for a product's primary image."""

    return f"/static/product-images/{product_id}"


def build_ranked_image_url(*, product_id: str, ordinal: int) -> str:
    """Return the stable route for a product image at a given 1-based ordinal."""

    return f"/static/product-images/{product_id}/{ordinal}"


def image_urls_for_runtime(
    *,
    runtime: object,
    canonical_product_key: str,
) -> tuple[str, ...]:
    """Read product image URLs from runtime when the image catalog is available."""

    product_image_catalog = cast(
        "ProductImageLookup | None",
        getattr(runtime, "product_image_catalog", None),
    )
    if product_image_catalog is None:
        return ()
    return product_image_catalog.image_urls_for_canonical_key(
        canonical_product_key=canonical_product_key
    )


def product_id_from_canonical_key(canonical_product_key: str) -> str:
    """Derive raw IKEA `product_id` from the repo canonical key.

    The current canonical key format is `<product_id>-<country>`, for example
    `28508-DE`. If the delimiter is absent, return the original value unchanged.
    """

    head, separator, _tail = canonical_product_key.rpartition("-")
    if separator and _tail.isalpha() and len(_tail) in {2, 3}:
        return head
    return canonical_product_key


def _discover_catalog_paths(*, output_root: Path) -> list[Path]:
    runs_root = output_root / "runs"
    if not runs_root.exists():
        return []
    catalog_paths: list[Path] = []
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        parquet_path = run_dir / "catalog.parquet"
        if parquet_path.exists():
            catalog_paths.append(parquet_path)
            continue
        jsonl_path = run_dir / "catalog.jsonl"
        if jsonl_path.exists():
            catalog_paths.append(jsonl_path)
    return catalog_paths


def _load_indexed_images(*, catalog_path: Path) -> tuple[IndexedProductImage, ...]:
    if catalog_path.suffix == ".parquet":
        return _load_indexed_images_from_parquet(catalog_path=catalog_path)
    return _load_indexed_images_from_jsonl(catalog_path=catalog_path)


def _load_indexed_images_from_parquet(*, catalog_path: Path) -> tuple[IndexedProductImage, ...]:
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            """
            SELECT
                CAST(product_id AS VARCHAR),
                local_path,
                image_rank,
                COALESCE(is_og_image, FALSE),
                canonical_image_url
            FROM read_parquet(?)
            WHERE local_path IS NOT NULL
            """,
            [str(catalog_path)],
        ).fetchall()
    finally:
        connection.close()
    return tuple(
        indexed_image
        for row in rows
        if (indexed_image := _indexed_image_from_row(row=row)) is not None
    )


def _load_indexed_images_from_jsonl(*, catalog_path: Path) -> tuple[IndexedProductImage, ...]:
    indexed_images: list[IndexedProductImage] = []
    with catalog_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            loaded = json.loads(line)
            if not isinstance(loaded, dict):
                continue
            indexed_image = _indexed_image_from_mapping(mapping=loaded)
            if indexed_image is not None:
                indexed_images.append(indexed_image)
    return tuple(indexed_images)


def _indexed_image_from_row(*, row: tuple[object, ...]) -> IndexedProductImage | None:
    return _indexed_image_from_mapping(
        mapping={
            "product_id": row[0],
            "local_path": row[1],
            "image_rank": row[2],
            "is_og_image": row[3],
            "canonical_image_url": row[4],
        }
    )


def _indexed_image_from_mapping(*, mapping: dict[str, object]) -> IndexedProductImage | None:
    product_id = _str_or_none(mapping.get("product_id"))
    local_path_value = _str_or_none(mapping.get("local_path"))
    if product_id is None or local_path_value is None:
        return None
    local_path = Path(local_path_value).expanduser()
    if not local_path.exists():
        return None
    return IndexedProductImage(
        product_id=product_id,
        local_path=local_path.resolve(),
        image_rank=_int_or_none(mapping.get("image_rank")),
        is_og_image=bool(mapping.get("is_og_image")),
        canonical_image_url=_str_or_none(mapping.get("canonical_image_url")),
    )


def _image_sort_key(indexed_image: IndexedProductImage) -> tuple[int, int, str]:
    return (
        0 if indexed_image.is_og_image else 1,
        indexed_image.image_rank if indexed_image.image_rank is not None else 2**31 - 1,
        indexed_image.canonical_image_url or "",
    )


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
