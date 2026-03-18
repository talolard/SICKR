"""Spider for discovering product-only IKEA image metadata from product pages."""

from __future__ import annotations

from pathlib import Path

import scrapy

from ikea_image_catalog.extractors import extract_discovery_records
from ikea_image_catalog.jsonl_io import read_jsonl
from ikea_image_catalog.models import ProductSeed


class ProductImageDiscoverySpider(scrapy.Spider):
    """Visit product pages once and emit one discovery row per product image."""

    name = "product_image_discovery"

    def __init__(self, *, seeds_file: str, crawl_run_id: str) -> None:
        super().__init__()
        self._crawl_run_id = crawl_run_id
        self._seeds = [ProductSeed.from_dict(row) for row in read_jsonl(Path(seeds_file))]

    async def start(self):  # type: ignore[override]
        """Schedule one request per sampled product page."""

        for seed in self._seeds:
            yield scrapy.Request(
                url=seed.page_fetch_url,
                callback=self.parse_product_page,
                meta={"product_seed": seed.to_dict()},
            )

    def parse_product_page(self, response: scrapy.http.Response) -> dict[str, object]:
        """Extract product-only image rows from one fetched product page."""

        seed = ProductSeed.from_dict(response.meta["product_seed"])
        for record in extract_discovery_records(
            seed=seed,
            page_text=response.text,
            page_http_status=response.status,
            crawl_run_id=self._crawl_run_id,
        ):
            yield record.to_dict()
