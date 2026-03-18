"""Typed row models for the IKEA image catalog sidecar."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _list_of_strings(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str)]


@dataclass(slots=True)
class ProductSeed:
    """One product page input row for discovery crawling."""

    product_id: str
    repo_canonical_product_key: str | None
    product_name: str
    country: str
    source_page_url: str
    page_fetch_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> ProductSeed:
        return cls(
            product_id=str(raw["product_id"]),
            repo_canonical_product_key=(
                str(raw["repo_canonical_product_key"])
                if isinstance(raw.get("repo_canonical_product_key"), str)
                else None
            ),
            product_name=str(raw["product_name"]),
            country=str(raw["country"]),
            source_page_url=str(raw["source_page_url"]),
            page_fetch_url=str(raw["page_fetch_url"]),
        )


@dataclass(slots=True)
class DiscoveryRecord:
    """One discovered product image row before download enrichment."""

    crawl_run_id: str
    scraped_at: str
    product_id: str
    repo_canonical_product_key: str | None
    product_name: str
    country: str
    source_page_url: str
    page_fetch_url: str
    page_canonical_url: str | None
    page_article_number: str | None
    page_title: str | None
    page_product_name: str | None
    page_og_image_url: str | None
    page_gallery_image_count: int
    page_http_status: int
    image_asset_key: str
    canonical_image_url: str
    variant_urls: list[str] = field(default_factory=list)
    variant_query_codes: list[str] = field(default_factory=list)
    image_rank: int = 0
    image_role: str | None = None
    is_og_image: bool = False
    extraction_source: str = "unknown"
    extraction_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> DiscoveryRecord:
        return cls(
            crawl_run_id=str(raw["crawl_run_id"]),
            scraped_at=str(raw["scraped_at"]),
            product_id=str(raw["product_id"]),
            repo_canonical_product_key=(
                str(raw["repo_canonical_product_key"])
                if isinstance(raw.get("repo_canonical_product_key"), str)
                else None
            ),
            product_name=str(raw["product_name"]),
            country=str(raw["country"]),
            source_page_url=str(raw["source_page_url"]),
            page_fetch_url=str(raw["page_fetch_url"]),
            page_canonical_url=(
                str(raw["page_canonical_url"])
                if isinstance(raw.get("page_canonical_url"), str)
                else None
            ),
            page_article_number=(
                str(raw["page_article_number"])
                if isinstance(raw.get("page_article_number"), str)
                else None
            ),
            page_title=str(raw["page_title"]) if isinstance(raw.get("page_title"), str) else None,
            page_product_name=(
                str(raw["page_product_name"])
                if isinstance(raw.get("page_product_name"), str)
                else None
            ),
            page_og_image_url=(
                str(raw["page_og_image_url"])
                if isinstance(raw.get("page_og_image_url"), str)
                else None
            ),
            page_gallery_image_count=int(raw["page_gallery_image_count"]),
            page_http_status=int(raw["page_http_status"]),
            image_asset_key=str(raw["image_asset_key"]),
            canonical_image_url=str(raw["canonical_image_url"]),
            variant_urls=_list_of_strings(raw.get("variant_urls")),
            variant_query_codes=_list_of_strings(raw.get("variant_query_codes")),
            image_rank=int(raw["image_rank"]),
            image_role=str(raw["image_role"]) if isinstance(raw.get("image_role"), str) else None,
            is_og_image=bool(raw["is_og_image"]),
            extraction_source=str(raw["extraction_source"]),
            extraction_warnings=_list_of_strings(raw.get("extraction_warnings")),
        )


@dataclass(slots=True)
class DownloadManifestRow:
    """One deduplicated asset that still needs a network download."""

    crawl_run_id: str
    image_asset_key: str
    canonical_image_url: str
    local_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> DownloadManifestRow:
        return cls(
            crawl_run_id=str(raw["crawl_run_id"]),
            image_asset_key=str(raw["image_asset_key"]),
            canonical_image_url=str(raw["canonical_image_url"]),
            local_path=str(raw["local_path"]),
        )


@dataclass(slots=True)
class DownloadRecord:
    """One asset-level download or cache result row."""

    crawl_run_id: str
    image_asset_key: str
    canonical_image_url: str
    download_status: str
    downloaded_at: str
    local_path: str | None
    storage_uri: str | None
    download_http_status: int | None = None
    content_type: str | None = None
    content_length_bytes: int | None = None
    etag: str | None = None
    cache_control: str | None = None
    sha256: str | None = None
    width_px: int | None = None
    height_px: int | None = None
    image_format: str | None = None
    color_mode: str | None = None
    files_pipeline_checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> DownloadRecord:
        return cls(
            crawl_run_id=str(raw["crawl_run_id"]),
            image_asset_key=str(raw["image_asset_key"]),
            canonical_image_url=str(raw["canonical_image_url"]),
            download_status=str(raw["download_status"]),
            downloaded_at=str(raw["downloaded_at"]),
            local_path=str(raw["local_path"]) if isinstance(raw.get("local_path"), str) else None,
            storage_uri=str(raw["storage_uri"])
            if isinstance(raw.get("storage_uri"), str)
            else None,
            download_http_status=(
                int(raw["download_http_status"])
                if raw.get("download_http_status") is not None
                else None
            ),
            content_type=str(raw["content_type"])
            if isinstance(raw.get("content_type"), str)
            else None,
            content_length_bytes=(
                int(raw["content_length_bytes"])
                if raw.get("content_length_bytes") is not None
                else None
            ),
            etag=str(raw["etag"]) if isinstance(raw.get("etag"), str) else None,
            cache_control=(
                str(raw["cache_control"]) if isinstance(raw.get("cache_control"), str) else None
            ),
            sha256=str(raw["sha256"]) if isinstance(raw.get("sha256"), str) else None,
            width_px=int(raw["width_px"]) if raw.get("width_px") is not None else None,
            height_px=int(raw["height_px"]) if raw.get("height_px") is not None else None,
            image_format=str(raw["image_format"])
            if isinstance(raw.get("image_format"), str)
            else None,
            color_mode=str(raw["color_mode"]) if isinstance(raw.get("color_mode"), str) else None,
            files_pipeline_checksum=(
                str(raw["files_pipeline_checksum"])
                if isinstance(raw.get("files_pipeline_checksum"), str)
                else None
            ),
        )
