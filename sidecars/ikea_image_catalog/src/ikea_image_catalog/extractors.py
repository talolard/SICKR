"""HTML extraction and URL normalization helpers for IKEA product images."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from parsel import Selector

from ikea_image_catalog.models import DiscoveryRecord, ProductSeed

PRODUCT_IMAGE_PATH_MARKER = "/images/products/"
PRODUCT_IMAGE_TYPE_SUFFIX = "PRODUCT_IMAGE"
FETCH_DATASET = "normal,allImages,prices,attributes"


@dataclass(slots=True)
class HydratedProductImage:
    """One product image object extracted from the hydrated page JSON."""

    url: str
    image_role: str | None


def current_timestamp() -> str:
    """Return an ISO-8601 timestamp in UTC."""

    return datetime.now(tz=UTC).isoformat()


def build_page_fetch_url(source_page_url: str) -> str:
    """Add the product-page dataset parameters needed for stable extraction."""

    split_result = urlsplit(source_page_url)
    query = parse_qs(split_result.query, keep_blank_values=True)
    query["type"] = ["xml"]
    query["dataset"] = [FETCH_DATASET]
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query, doseq=True),
            "",
        )
    )


def canonicalize_image_url(image_url: str) -> str:
    """Drop query/fragment so image identity uses the master path."""

    split_result = urlsplit(image_url)
    return urlunsplit((split_result.scheme, split_result.netloc, split_result.path, "", ""))


def image_asset_key_from_url(image_url: str) -> str:
    """Build a stable, locale-agnostic asset key from an IKEA product image URL."""

    canonical_url = canonicalize_image_url(image_url)
    split_result = urlsplit(canonical_url)
    marker_index = split_result.path.find(PRODUCT_IMAGE_PATH_MARKER)
    if marker_index == -1:
        msg = f"not an IKEA product image URL: {image_url}"
        raise ValueError(msg)
    return split_result.path[marker_index + len(PRODUCT_IMAGE_PATH_MARKER) :].lower()


def collect_variant_urls(page_text: str, canonical_url: str) -> list[str]:
    """Collect observed size/query variants for one known product image on the page."""

    pattern = re.compile(rf"{re.escape(canonical_url)}(?:\\?[^\"'<>\\s]+)?")
    matches: OrderedDict[str, None] = OrderedDict([(canonical_url, None)])
    for match in pattern.finditer(page_text):
        matches.setdefault(match.group(0), None)
    return list(matches.keys())


def variant_query_codes(variant_urls: list[str]) -> list[str]:
    """Return unique observed `f=` query codes in first-seen order."""

    observed: OrderedDict[str, None] = OrderedDict()
    for variant_url in variant_urls:
        for value in parse_qs(urlsplit(variant_url).query).get("f", []):
            observed.setdefault(value, None)
    return list(observed.keys())


def _iter_nested_dicts(raw: object) -> Iterator[dict[str, object]]:
    if isinstance(raw, dict):
        yield raw
        for value in raw.values():
            yield from _iter_nested_dicts(value)
        return
    if isinstance(raw, list):
        for value in raw:
            yield from _iter_nested_dicts(value)


def _load_json_script(raw_text: str) -> object | None:
    stripped = raw_text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def extract_hydrated_product_images(selector: Selector) -> list[HydratedProductImage]:
    """Extract product-gallery images from IKEA hydration JSON only."""

    results: OrderedDict[str, HydratedProductImage] = OrderedDict()
    for script_text in selector.css('script[type="text/hydration"]::text').getall():
        payload = _load_json_script(script_text)
        if payload is None:
            continue
        for raw_object in _iter_nested_dicts(payload):
            image_url = raw_object.get("url")
            image_role = raw_object.get("type")
            if not isinstance(image_url, str) or PRODUCT_IMAGE_PATH_MARKER not in image_url:
                continue
            if not isinstance(image_role, str) or not image_role.endswith(
                PRODUCT_IMAGE_TYPE_SUFFIX
            ):
                continue
            canonical_url = canonicalize_image_url(image_url)
            results.setdefault(
                canonical_url,
                HydratedProductImage(url=canonical_url, image_role=image_role),
            )
    return list(results.values())


def _iter_json_ld_products(selector: Selector) -> Iterator[dict[str, object]]:
    for script_text in selector.css('script[type="application/ld+json"]::text').getall():
        payload = _load_json_script(script_text)
        if payload is None:
            continue
        if isinstance(payload, list):
            for item in payload:
                yield from _iter_nested_dicts(item)
            continue
        yield from _iter_nested_dicts(payload)


def extract_json_ld_product_images(selector: Selector) -> list[str]:
    """Extract product image URLs from Product JSON-LD blocks only."""

    urls: OrderedDict[str, None] = OrderedDict()
    for raw_object in _iter_json_ld_products(selector):
        if raw_object.get("@type") != "Product":
            continue
        raw_images = raw_object.get("image")
        if isinstance(raw_images, list):
            for raw_image in raw_images:
                if isinstance(raw_image, dict):
                    image_url = raw_image.get("contentUrl") or raw_image.get("url")
                elif isinstance(raw_image, str):
                    image_url = raw_image
                else:
                    continue
                if isinstance(image_url, str) and PRODUCT_IMAGE_PATH_MARKER in image_url:
                    urls.setdefault(canonicalize_image_url(image_url), None)
    return list(urls.keys())


def extract_page_article_number(page_text: str, page_canonical_url: str | None) -> str | None:
    """Extract the page's article number from structured data or the canonical URL."""

    for pattern in (
        r'"viewItem":\{"id":"(\d+)"',
        r'"product_ids":\["(\d+)"\]',
        r'"articleNumber":\{"label":"[^"]+","value":"([0-9.]+)"\}',
    ):
        match = re.search(pattern, page_text)
        if match is not None:
            return match.group(1).replace(".", "")
    if page_canonical_url is None:
        return None
    url_match = re.search(r"-(\d{8})/?$", page_canonical_url)
    if url_match is None:
        return None
    return url_match.group(1)


def _normalized_page_product_name(raw_title: str | None) -> str | None:
    if raw_title is None:
        return None
    return raw_title.removesuffix(" - IKEA").strip() or None


def extract_discovery_records(
    *,
    seed: ProductSeed,
    page_text: str,
    page_http_status: int,
    crawl_run_id: str,
) -> list[DiscoveryRecord]:
    """Extract one discovery row per product image from the fetched page."""

    selector = Selector(text=page_text)
    page_canonical_url = selector.css('link[rel="canonical"]::attr(href)').get()
    raw_page_title = selector.css("title::text").get()
    raw_og_title = selector.css('meta[property="og:title"]::attr(content)').get()
    raw_og_image = selector.css('meta[property="og:image"]::attr(content)').get()
    page_og_image_url = canonicalize_image_url(raw_og_image) if raw_og_image is not None else None
    page_article_number = extract_page_article_number(page_text, page_canonical_url)
    page_product_name = _normalized_page_product_name(raw_og_title or raw_page_title)
    warnings: list[str] = []

    hydrated_images = extract_hydrated_product_images(selector)
    json_ld_images = extract_json_ld_product_images(selector)
    if not hydrated_images:
        warnings.append("hydration_product_images_missing")
    if not json_ld_images:
        warnings.append("jsonld_product_images_missing")

    records_by_url: OrderedDict[str, DiscoveryRecord] = OrderedDict()
    scraped_at = current_timestamp()

    def add_or_update_record(
        *,
        image_url: str,
        image_role: str | None,
        extraction_source: str,
        mark_as_og: bool,
    ) -> None:
        canonical_image_url = canonicalize_image_url(image_url)
        if PRODUCT_IMAGE_PATH_MARKER not in canonical_image_url:
            return
        image_asset_key = image_asset_key_from_url(canonical_image_url)
        if canonical_image_url in records_by_url:
            if mark_as_og:
                records_by_url[canonical_image_url].is_og_image = True
            return
        variant_urls = collect_variant_urls(page_text, canonical_image_url)
        records_by_url[canonical_image_url] = DiscoveryRecord(
            crawl_run_id=crawl_run_id,
            scraped_at=scraped_at,
            product_id=seed.product_id,
            repo_canonical_product_key=seed.repo_canonical_product_key,
            product_name=seed.product_name,
            country=seed.country,
            source_page_url=seed.source_page_url,
            page_fetch_url=seed.page_fetch_url,
            page_canonical_url=page_canonical_url,
            page_article_number=page_article_number,
            page_title=raw_page_title.strip() if raw_page_title is not None else None,
            page_product_name=page_product_name,
            page_og_image_url=page_og_image_url,
            page_gallery_image_count=0,
            page_http_status=page_http_status,
            image_asset_key=image_asset_key,
            canonical_image_url=canonical_image_url,
            variant_urls=variant_urls,
            variant_query_codes=variant_query_codes(variant_urls),
            image_rank=0,
            image_role=image_role,
            is_og_image=mark_as_og,
            extraction_source=extraction_source,
            extraction_warnings=list(warnings),
        )

    for hydrated_image in hydrated_images:
        add_or_update_record(
            image_url=hydrated_image.url,
            image_role=hydrated_image.image_role,
            extraction_source="hydration_product_image",
            mark_as_og=page_og_image_url == hydrated_image.url,
        )

    for json_ld_image in json_ld_images:
        add_or_update_record(
            image_url=json_ld_image,
            image_role=None,
            extraction_source="jsonld_product_image",
            mark_as_og=page_og_image_url == json_ld_image,
        )

    if page_og_image_url is not None:
        add_or_update_record(
            image_url=page_og_image_url,
            image_role=None,
            extraction_source="og_image_fallback",
            mark_as_og=True,
        )

    records = list(records_by_url.values())
    if not records:
        warnings.append("no_product_images_found")
        return []
    for index, record in enumerate(records, start=1):
        record.image_rank = index
        record.page_gallery_image_count = len(records)
        record.extraction_warnings = list(warnings)
    return records
