from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image
import pytest

from ikea_image_catalog.cli import (
    _prior_discovery_files,
    _merge_catalog_rows,
    _prepare_download_stage,
    _run_scrapy_stage,
    _run_summary,
    _scrapy_response_status_counts,
    _seen_source_page_urls,
    main,
)
from ikea_image_catalog.jsonl_io import write_jsonl
from ikea_image_catalog.models import DiscoveryRecord, DownloadRecord
from ikea_image_catalog.paths import DEFAULT_OUTPUT_ROOT, local_image_path, resolve_output_root


def _discovery_record(
    *, product_id: str = "00179535", image_asset_key: str = "ordning.jpg"
) -> DiscoveryRecord:
    return DiscoveryRecord(
        crawl_run_id="test-run",
        scraped_at=datetime(2026, 3, 18, tzinfo=UTC).isoformat(),
        product_id=product_id,
        repo_canonical_product_key=None,
        product_name="ORDNING",
        country="Australia",
        source_page_url="https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/",
        page_fetch_url="https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/?type=xml&dataset=normal%2CallImages%2Cprices%2Cattributes",
        page_canonical_url="https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/",
        page_article_number="00179535",
        page_title="ORDNING dish drainer - IKEA",
        page_product_name="ORDNING",
        page_og_image_url="https://www.ikea.com/au/en/images/products/ordning.jpg",
        page_gallery_image_count=1,
        page_http_status=200,
        image_asset_key=image_asset_key,
        canonical_image_url=f"https://www.ikea.com/au/en/images/products/{image_asset_key}",
        variant_urls=[f"https://www.ikea.com/au/en/images/products/{image_asset_key}?f=u"],
        variant_query_codes=["u"],
        image_rank=1,
        image_role="MAIN_PRODUCT_IMAGE",
        is_og_image=True,
        extraction_source="hydration_product_image",
        extraction_warnings=[],
    )


def _download_record(
    *, image_asset_key: str = "ordning.jpg", sha256: str = "abc123"
) -> DownloadRecord:
    return DownloadRecord(
        crawl_run_id="test-run",
        image_asset_key=image_asset_key,
        canonical_image_url=f"https://www.ikea.com/au/en/images/products/{image_asset_key}",
        download_status="downloaded",
        downloaded_at=datetime(2026, 3, 18, tzinfo=UTC).isoformat(),
        local_path=f"/tmp/{image_asset_key}",
        storage_uri=f"file:///tmp/{image_asset_key}",
        download_http_status=200,
        content_type="image/jpeg",
        content_length_bytes=123,
        etag="etag",
        cache_control="max-age=60",
        sha256=sha256,
        width_px=100,
        height_px=200,
        image_format="JPEG",
        color_mode="RGB",
    )


def test_resolve_output_root_defaults_and_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("IKEA_IMAGE_CATALOG_OUTPUT_ROOT", raising=False)
    assert resolve_output_root() == DEFAULT_OUTPUT_ROOT

    override_root = tmp_path / "override"
    monkeypatch.setenv("IKEA_IMAGE_CATALOG_OUTPUT_ROOT", str(override_root))
    assert resolve_output_root() == override_root.resolve()


def test_prepare_download_stage_uses_cached_assets(tmp_path: Path) -> None:
    images_root = tmp_path / "images"
    discovery_record = _discovery_record(image_asset_key="nested/ordning.jpg")
    cached_path = local_image_path(images_root, discovery_record.image_asset_key)
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (3, 2), color="white")
    image.save(cached_path, format="JPEG")

    cached_records, manifest_rows = _prepare_download_stage(
        paths=SimpleNamespace(images_root=images_root),
        discovery_records=[discovery_record],
    )

    assert len(cached_records) == 1
    assert cached_records[0].download_status == "cached_local"
    assert cached_records[0].width_px == 3
    assert cached_records[0].height_px == 2
    assert manifest_rows == []


def test_merge_catalog_rows_flags_asset_key_conflicts() -> None:
    discovery_record = _discovery_record()
    matching_download = _download_record(sha256="aaa")
    conflicting_download = _download_record(sha256="bbb")

    merged_rows = _merge_catalog_rows(
        discovery_records=[discovery_record],
        download_records=[matching_download, conflicting_download],
    )

    assert len(merged_rows) == 1
    assert merged_rows[0]["download_status"] == "downloaded"
    assert merged_rows[0]["asset_key_conflict"] is True


def test_scrapy_response_status_counts_extracts_statuses() -> None:
    counts = _scrapy_response_status_counts(
        {
            "downloader/response_status_count/200": 12,
            "downloader/response_status_count/301": 3,
            "other": 99,
        }
    )

    assert counts == {200: 12, 301: 3}


def test_run_summary_prefers_scrapy_status_counts(tmp_path: Path) -> None:
    discovery_record = _discovery_record()
    download_record = _download_record()
    summary = _run_summary(
        crawl_run_id="test-run",
        seeds=[],
        discovery_records=[discovery_record],
        download_records=[download_record],
        discovery_stats={
            "downloader/response_status_count/200": 10,
            "downloader/response_status_count/301": 2,
        },
        download_stats={"downloader/response_status_count/200": 7},
        paths=SimpleNamespace(
            output_root=tmp_path,
            run_root=tmp_path / "run",
            catalog_jsonl=tmp_path / "catalog.jsonl",
            catalog_parquet=tmp_path / "catalog.parquet",
            downloads_jsonl=tmp_path / "downloads.jsonl",
            discovered_jsonl=tmp_path / "discovered.jsonl",
        ),
    )

    assert summary["page_http_status_counts"] == {200: 10, 301: 2}
    assert summary["download_http_status_counts"] == {200: 1}


def test_run_scrapy_stage_uses_live_src_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> None:
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]

    monkeypatch.setattr("subprocess.run", fake_run)

    _run_scrapy_stage(
        spider_name="product_image_discovery",
        feed_path=tmp_path / "feed.jsonl",
        jobdir_path=tmp_path / "jobdir",
        stats_path=tmp_path / "stats.json",
        spider_args=[("seeds_file", "seed.jsonl"), ("crawl_run_id", "test-run")],
    )

    assert captured["command"][:3] == [captured["command"][0], "-m", "scrapy"]
    assert captured["cwd"].name == "ikea_image_catalog"
    assert captured["env"]["SCRAPY_SETTINGS_MODULE"] == "ikea_image_catalog.settings"
    assert str((captured["cwd"] / "src").resolve()) in captured["env"]["PYTHONPATH"].split(":")


def test_seen_source_page_urls_excludes_current_run(tmp_path: Path) -> None:
    completed_run = tmp_path / "runs" / "pilot-1000"
    current_run = tmp_path / "runs" / "all-products-1"
    write_jsonl(
        completed_run / "discovered.jsonl",
        [
            {"source_page_url": "https://www.ikea.com/de/en/p/foo-1/"},
            {"source_page_url": "https://www.ikea.com/us/en/p/bar-2/"},
        ],
    )
    write_jsonl(
        current_run / "discovered.jsonl",
        [{"source_page_url": "https://www.ikea.com/fr/en/p/baz-3/"}],
    )

    files = _prior_discovery_files(tmp_path, exclude_run_id="all-products-1")
    assert files == [completed_run / "discovered.jsonl"]
    assert _seen_source_page_urls(tmp_path, exclude_run_id="all-products-1") == {
        "https://www.ikea.com/de/en/p/foo-1/",
        "https://www.ikea.com/us/en/p/bar-2/",
    }


def test_main_rejects_all_with_limit() -> None:
    with pytest.raises(SystemExit):
        main(["crawl", "--all", "--limit", "10"])
