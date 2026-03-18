"""Scrapy media pipelines for IKEA product image downloads."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from scrapy import Request
from scrapy.http import Response
from scrapy.pipelines.files import FilesPipeline
from twisted.python.failure import Failure


class ProductImageFilesPipeline(FilesPipeline):
    """Store canonical product images and enrich exported rows with file metadata."""

    def get_media_requests(
        self,
        item: dict[str, object],
        info: FilesPipeline.SpiderInfo,
    ) -> list[Request]:
        canonical_image_url = item.get("canonical_image_url")
        image_asset_key = item.get("image_asset_key")
        if not isinstance(canonical_image_url, str) or not isinstance(image_asset_key, str):
            return []
        return [
            Request(
                url=canonical_image_url,
                meta={"image_asset_key": image_asset_key},
            )
        ]

    def file_path(
        self,
        request: Request,
        response: Response | None = None,
        info: FilesPipeline.SpiderInfo | None = None,
        *,
        item: Any = None,
    ) -> str:
        image_asset_key = request.meta["image_asset_key"]
        return f"masters/{image_asset_key}"

    def media_downloaded(
        self,
        response: Response,
        request: Request,
        info: FilesPipeline.SpiderInfo,
        *,
        item: Any = None,
    ) -> dict[str, object]:
        result = super().media_downloaded(response, request, info, item=item)
        result["download_http_status"] = response.status
        result["content_type"] = response.headers.get("Content-Type", b"").decode("utf-8") or None
        result["etag"] = response.headers.get("ETag", b"").decode("utf-8") or None
        result["cache_control"] = response.headers.get("Cache-Control", b"").decode("utf-8") or None
        result["content_length_bytes"] = len(response.body)
        return result

    def item_completed(
        self,
        results: list[tuple[bool, dict[str, object] | Failure]],
        item: dict[str, object],
        info: FilesPipeline.SpiderInfo,
    ) -> dict[str, object]:
        if not results:
            return self._failed_item(item=item, failure=None)
        success, payload = results[0]
        if not success:
            return self._failed_item(item=item, failure=payload)

        assert isinstance(payload, dict)
        local_path = Path(self.store.basedir) / str(payload["path"])
        raw_bytes = local_path.read_bytes()
        with Image.open(BytesIO(raw_bytes)) as image:
            width_px, height_px = image.size
            image_format = image.format
            color_mode = image.mode

        pipeline_status = str(payload["status"])
        download_status = "downloaded" if pipeline_status == "downloaded" else "cached_pipeline"
        item.update(
            {
                "download_status": download_status,
                "downloaded_at": datetime.now(tz=UTC).isoformat(),
                "local_path": str(local_path),
                "storage_uri": local_path.resolve().as_uri(),
                "download_http_status": payload.get("download_http_status"),
                "content_type": payload.get("content_type"),
                "content_length_bytes": payload.get("content_length_bytes"),
                "etag": payload.get("etag"),
                "cache_control": payload.get("cache_control"),
                "sha256": sha256(raw_bytes).hexdigest(),
                "width_px": width_px,
                "height_px": height_px,
                "image_format": image_format,
                "color_mode": color_mode,
                "files_pipeline_checksum": payload.get("checksum"),
            }
        )
        return item

    def _failed_item(
        self,
        *,
        item: dict[str, object],
        failure: dict[str, object] | Failure | None,
    ) -> dict[str, object]:
        response = None
        if isinstance(failure, Failure):
            response = getattr(failure.value, "response", None)
        item.update(
            {
                "download_status": "download_failed",
                "downloaded_at": None,
                "local_path": None,
                "storage_uri": None,
                "download_http_status": getattr(response, "status", None),
                "content_type": None,
                "content_length_bytes": None,
                "etag": None,
                "cache_control": None,
                "sha256": None,
                "width_px": None,
                "height_px": None,
                "image_format": None,
                "color_mode": None,
                "files_pipeline_checksum": None,
            }
        )
        return item
