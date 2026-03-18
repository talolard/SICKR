"""Spider for downloading deduplicated IKEA master image assets."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import scrapy

from ikea_image_catalog.jsonl_io import read_jsonl
from ikea_image_catalog.models import DownloadManifestRow


class ProductImageDownloadSpider(scrapy.Spider):
    """Download only missing deduplicated assets from a manifest."""

    name = "product_image_download"
    bootstrap_url = "https://www.ikea.com/robots.txt"
    custom_settings = {
        "ITEM_PIPELINES": {
            "ikea_image_catalog.pipelines.ProductImageFilesPipeline": 100,
        }
    }

    def __init__(self, *, manifest_file: str) -> None:
        super().__init__()
        self._manifest_rows = [
            DownloadManifestRow.from_dict(row) for row in read_jsonl(Path(manifest_file))
        ]

    async def start(self):  # type: ignore[override]
        """Bootstrap the item pipeline from one cheap request."""

        if not self._manifest_rows:
            return
        yield scrapy.Request(
            url=self.bootstrap_url,
            callback=self.emit_manifest_rows,
            dont_filter=True,
        )

    def emit_manifest_rows(self, response: scrapy.http.Response) -> Iterator[dict[str, object]]:
        """Emit one manifest item per missing canonical asset."""

        del response
        for row in self._manifest_rows:
            yield {
                **row.to_dict(),
                "download_urls": [row.canonical_image_url],
            }
