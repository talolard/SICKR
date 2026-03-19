"""Product image catalog lookup for search and bundle rendering."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Literal, Protocol, cast

import duckdb
from sqlalchemy import Engine, text

logger = getLogger(__name__)

_DEFAULT_PRODUCT_IMAGE_ORDINAL = 1


@dataclass(frozen=True, slots=True)
class IndexedProductImage:
    """One local or remotely served image ranked for a raw IKEA product id."""

    product_id: str
    local_path: Path | None
    image_rank: int | None
    is_og_image: bool
    public_url: str | None
    storage_backend_kind: str


class ProductImageLookup(Protocol):
    """Minimal image lookup surface used by runtime helpers and routes."""

    def image_urls_for_canonical_key(self, *, canonical_product_key: str) -> tuple[str, ...]:
        """Return image URLs for one canonical product key."""

    def resolve_image_path(self, *, product_id: str, ordinal: int | None = None) -> Path | None:
        """Return one local image path for a product and optional ordinal."""


@dataclass(frozen=True, slots=True)
class ProductImageCatalog:
    """In-memory index of product images keyed by raw `product_id`."""

    output_root: Path
    images_by_product_id: dict[str, tuple[IndexedProductImage, ...]]
    serving_strategy: Literal["backend_proxy", "direct_public_url"] = "backend_proxy"
    base_url: str | None = None

    @classmethod
    def empty(cls, *, output_root: Path) -> ProductImageCatalog:
        """Return an empty index rooted at the configured catalog directory."""

        return cls(output_root=output_root, images_by_product_id={})

    @classmethod
    def from_database(
        cls,
        *,
        engine: Engine,
        output_root: Path,
        serving_strategy: Literal["backend_proxy", "direct_public_url"],
        base_url: str | None,
    ) -> ProductImageCatalog:
        """Build an index from the seeded Postgres image catalog tables."""

        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT
                        product_id,
                        local_path,
                        image_rank,
                        is_og_image,
                        public_url,
                        storage_backend_kind
                    FROM catalog.product_images
                    ORDER BY product_id, image_rank NULLS LAST, image_asset_key
                    """
                )
            ).fetchall()

        images_by_product_id: dict[str, list[IndexedProductImage]] = defaultdict(list)
        for row in rows:
            product_id = _str_or_none(row[0])
            if product_id is None:
                continue
            local_path_value = _str_or_none(row[1])
            local_path = None
            if local_path_value is not None:
                candidate = Path(local_path_value).expanduser()
                if candidate.exists():
                    local_path = candidate.resolve()
            images_by_product_id[product_id].append(
                IndexedProductImage(
                    product_id=product_id,
                    local_path=local_path,
                    image_rank=_int_or_none(row[2]),
                    is_og_image=bool(row[3]),
                    public_url=_str_or_none(row[4]),
                    storage_backend_kind=_str_or_none(row[5]) or "local_shared_root",
                )
            )

        return cls(
            output_root=output_root,
            images_by_product_id={
                product_id: tuple(sorted(images, key=_image_sort_key))
                for product_id, images in images_by_product_id.items()
            },
            serving_strategy=serving_strategy,
            base_url=base_url,
        )

    @classmethod
    def from_output_root(cls, *, output_root: Path) -> ProductImageCatalog:
        """Build a legacy file-backed index from completed sidecar run outputs."""

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
                local_path = indexed_image.local_path
                if local_path is None:
                    continue
                current = images_by_product_id[indexed_image.product_id].get(local_path)
                if current is None or _image_sort_key(indexed_image) < _image_sort_key(current):
                    images_by_product_id[indexed_image.product_id][local_path] = indexed_image
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
        return tuple(
            _build_image_url(
                indexed_image=indexed_image,
                product_id=product_id,
                ordinal=ordinal,
                serving_strategy=self.serving_strategy,
                base_url=self.base_url,
            )
            for ordinal, indexed_image in enumerate(indexed_images, start=1)
        )

    def resolve_image_path(self, *, product_id: str, ordinal: int | None = None) -> Path | None:
        """Resolve one local file path for a product and optional 1-based ordinal."""

        indexed_images = self.images_by_product_id.get(product_id, ())
        if not indexed_images:
            return None
        target_ordinal = _DEFAULT_PRODUCT_IMAGE_ORDINAL if ordinal is None else ordinal
        if target_ordinal < 1 or target_ordinal > len(indexed_images):
            return None
        return indexed_images[target_ordinal - 1].local_path


def build_primary_image_url(*, product_id: str, base_url: str | None = None) -> str:
    """Return the stable route for a product's primary image."""

    return _join_base_url(base_url=base_url, path=f"/static/product-images/{product_id}")


def build_ranked_image_url(*, product_id: str, ordinal: int, base_url: str | None = None) -> str:
    """Return the stable route for a product image at a given 1-based ordinal."""

    return _join_base_url(
        base_url=base_url,
        path=f"/static/product-images/{product_id}/{ordinal}",
    )


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
    """Derive raw IKEA `product_id` from the repo canonical key."""

    head, separator, tail = canonical_product_key.rpartition("-")
    if separator and tail.isalpha() and len(tail) in {2, 3}:
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
        public_url=_str_or_none(mapping.get("canonical_image_url")),
        storage_backend_kind="local_shared_root",
    )


def _image_sort_key(indexed_image: IndexedProductImage) -> tuple[int, int, str]:
    return (
        0 if indexed_image.is_og_image else 1,
        indexed_image.image_rank if indexed_image.image_rank is not None else 2**31 - 1,
        indexed_image.public_url or "",
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


def _join_base_url(*, base_url: str | None, path: str) -> str:
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"


def _build_image_url(
    *,
    indexed_image: IndexedProductImage,
    product_id: str,
    ordinal: int,
    serving_strategy: Literal["backend_proxy", "direct_public_url"],
    base_url: str | None,
) -> str:
    if serving_strategy == "direct_public_url" and indexed_image.public_url:
        return indexed_image.public_url
    if ordinal == 1:
        return build_primary_image_url(product_id=product_id, base_url=base_url)
    return build_ranked_image_url(product_id=product_id, ordinal=ordinal, base_url=base_url)
