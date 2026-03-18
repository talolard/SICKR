"""CLI entrypoints for the IKEA image catalog sidecar."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
from collections import Counter, OrderedDict
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import duckdb
from PIL import Image

from ikea_image_catalog.jsonl_io import read_jsonl, write_jsonl
from ikea_image_catalog.models import (
    DiscoveryRecord,
    DownloadManifestRow,
    DownloadRecord,
    ProductSeed,
)
from ikea_image_catalog.paths import (
    RunPaths,
    build_run_paths,
    local_image_path,
    resolve_output_root,
)
from ikea_image_catalog.sampling import load_product_seeds


def _now_compact() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _project_root().parents[1]


def _run_scrapy_stage(
    *,
    spider_name: str,
    feed_path: Path,
    jobdir_path: Path,
    stats_path: Path,
    spider_args: Sequence[tuple[str, str]],
    setting_args: Sequence[tuple[str, str]] = (),
) -> None:
    project_root = _project_root()
    src_root = project_root / "src"
    env = os.environ.copy()
    pythonpath_parts = [str(src_root)]
    if existing_pythonpath := env.get("PYTHONPATH"):
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["SCRAPY_SETTINGS_MODULE"] = "ikea_image_catalog.settings"
    command = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        spider_name,
        "-O",
        f"{feed_path}:jsonlines",
        "-s",
        f"JOBDIR={jobdir_path}",
        "-s",
        f"RUN_STATS_PATH={stats_path}",
    ]
    for key, value in setting_args:
        command.extend(["-s", f"{key}={value}"])
    for key, value in spider_args:
        command.extend(["-a", f"{key}={value}"])
    subprocess.run(command, check=True, cwd=project_root, env=env)


def _write_seeds(paths: RunPaths, seeds: list[ProductSeed]) -> None:
    write_jsonl(paths.seeds_jsonl, [seed.to_dict() for seed in seeds])


def _prior_discovery_files(output_root: Path, *, exclude_run_id: str) -> list[Path]:
    """Return discovery files from prior runs that can seed incremental skipping."""

    run_roots = sorted((output_root / "runs").glob("*"))
    return [
        run_root / "discovered.jsonl"
        for run_root in run_roots
        if run_root.name != exclude_run_id and (run_root / "discovered.jsonl").exists()
    ]


def _seen_source_page_urls(output_root: Path, *, exclude_run_id: str) -> set[str]:
    """Load previously discovered source page URLs from prior runs."""

    seen_urls: set[str] = set()
    for discovery_file in _prior_discovery_files(output_root, exclude_run_id=exclude_run_id):
        for row in read_jsonl(discovery_file):
            source_page_url = row.get("source_page_url")
            if isinstance(source_page_url, str):
                seen_urls.add(source_page_url)
    return seen_urls


def _cached_download_record(
    *, crawl_run_id: str, image_asset_key: str, canonical_image_url: str, path: Path
) -> DownloadRecord:
    raw_bytes = path.read_bytes()
    guessed_content_type, _ = mimetypes.guess_type(str(path))
    with Image.open(BytesIO(raw_bytes)) as image:
        width_px, height_px = image.size
        image_format = image.format
        color_mode = image.mode
    return DownloadRecord(
        crawl_run_id=crawl_run_id,
        image_asset_key=image_asset_key,
        canonical_image_url=canonical_image_url,
        download_status="cached_local",
        downloaded_at=datetime.now(tz=UTC).isoformat(),
        local_path=str(path),
        storage_uri=path.resolve().as_uri(),
        download_http_status=None,
        content_type=guessed_content_type,
        content_length_bytes=len(raw_bytes),
        etag=None,
        cache_control=None,
        sha256=sha256(raw_bytes).hexdigest(),
        width_px=width_px,
        height_px=height_px,
        image_format=image_format,
        color_mode=color_mode,
        files_pipeline_checksum=None,
    )


def _prepare_download_stage(
    paths: RunPaths, discovery_records: list[DiscoveryRecord]
) -> tuple[list[DownloadRecord], list[DownloadManifestRow]]:
    grouped: OrderedDict[str, DiscoveryRecord] = OrderedDict()
    for record in discovery_records:
        grouped.setdefault(record.image_asset_key, record)

    cached_records: list[DownloadRecord] = []
    manifest_rows: list[DownloadManifestRow] = []
    for image_asset_key, record in grouped.items():
        target_path = local_image_path(paths.images_root, image_asset_key)
        if target_path.exists():
            cached_records.append(
                _cached_download_record(
                    crawl_run_id=record.crawl_run_id,
                    image_asset_key=image_asset_key,
                    canonical_image_url=record.canonical_image_url,
                    path=target_path,
                )
            )
            continue
        manifest_rows.append(
            DownloadManifestRow(
                crawl_run_id=record.crawl_run_id,
                image_asset_key=image_asset_key,
                canonical_image_url=record.canonical_image_url,
                local_path=str(target_path),
            )
        )
    return cached_records, manifest_rows


def _load_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_catalog_parquet(catalog_rows: list[dict[str, Any]], paths: RunPaths) -> None:
    """Write a Parquet copy of the final JSONL catalog for downstream analytics."""

    if not catalog_rows:
        connection = duckdb.connect()
        connection.sql("SELECT * FROM (SELECT 1 AS placeholder) WHERE FALSE").write_parquet(
            str(paths.catalog_parquet)
        )
        connection.close()
        return
    connection = duckdb.connect()
    try:
        relation = connection.read_json(str(paths.catalog_jsonl), format="newline_delimited")
        relation.write_parquet(str(paths.catalog_parquet))
    finally:
        connection.close()


def _scrapy_response_status_counts(stats: dict[str, Any]) -> dict[int, int]:
    """Extract HTTP status counts from Scrapy's downloader stats keys."""

    counts: dict[int, int] = {}
    prefix = "downloader/response_status_count/"
    for key, value in stats.items():
        if not key.startswith(prefix):
            continue
        if not isinstance(value, int):
            continue
        status_code = int(key.removeprefix(prefix))
        counts[status_code] = value
    return counts


def _merge_catalog_rows(
    *,
    discovery_records: list[DiscoveryRecord],
    download_records: list[DownloadRecord],
) -> list[dict[str, Any]]:
    downloads_by_asset_key: dict[str, list[DownloadRecord]] = {}
    for download_record in download_records:
        downloads_by_asset_key.setdefault(download_record.image_asset_key, []).append(
            download_record
        )

    catalog_rows: list[dict[str, Any]] = []
    for discovery_record in discovery_records:
        candidate_downloads = downloads_by_asset_key.get(discovery_record.image_asset_key, [])
        chosen_download = candidate_downloads[0] if candidate_downloads else None
        distinct_sha256 = {row.sha256 for row in candidate_downloads if row.sha256 is not None}
        catalog_row = discovery_record.to_dict()
        if chosen_download is None:
            catalog_row.update(
                {
                    "download_status": "missing_download_record",
                    "downloaded_at": None,
                    "download_http_status": None,
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
                    "local_path": None,
                    "storage_uri": None,
                    "asset_key_conflict": False,
                }
            )
        else:
            catalog_row.update(chosen_download.to_dict())
            catalog_row["asset_key_conflict"] = len(distinct_sha256) > 1
        catalog_rows.append(catalog_row)
    return catalog_rows


def _run_summary(
    *,
    crawl_run_id: str,
    seeds: list[ProductSeed],
    discovery_records: list[DiscoveryRecord],
    download_records: list[DownloadRecord],
    discovery_stats: dict[str, Any],
    download_stats: dict[str, Any],
    paths: RunPaths,
) -> dict[str, Any]:
    page_status_counts = _scrapy_response_status_counts(discovery_stats) or dict(
        Counter(record.page_http_status for record in discovery_records)
    )
    download_status_counts = Counter(record.download_status for record in download_records)
    download_http_status_counts = dict(
        Counter(
            record.download_http_status
            for record in download_records
            if record.download_http_status is not None
        )
    )
    return {
        "crawl_run_id": crawl_run_id,
        "seed_count": len(seeds),
        "discovery_record_count": len(discovery_records),
        "unique_asset_count": len({record.image_asset_key for record in discovery_records}),
        "download_record_count": len(download_records),
        "cached_asset_count": download_status_counts.get("cached_local", 0)
        + download_status_counts.get("cached_pipeline", 0),
        "downloaded_asset_count": download_status_counts.get("downloaded", 0),
        "failed_asset_count": download_status_counts.get("download_failed", 0),
        "page_http_status_counts": dict(sorted(page_status_counts.items())),
        "download_http_status_counts": dict(sorted(download_http_status_counts.items())),
        "download_status_counts": dict(sorted(download_status_counts.items())),
        "discovery_stats": discovery_stats,
        "download_stats": download_stats,
        "output_root": str(paths.output_root),
        "run_root": str(paths.run_root),
        "catalog_jsonl": str(paths.catalog_jsonl),
        "catalog_parquet": str(paths.catalog_parquet),
        "downloads_jsonl": str(paths.downloads_jsonl),
        "discovered_jsonl": str(paths.discovered_jsonl),
    }


def _crawl_setting_args(
    *,
    concurrent_requests: int | None,
    concurrent_requests_per_domain: int | None,
    autothrottle_target_concurrency: float | None,
) -> list[tuple[str, str]]:
    """Translate optional crawl overrides into Scrapy `-s` settings."""

    setting_args: list[tuple[str, str]] = []
    if concurrent_requests is not None:
        setting_args.append(("CONCURRENT_REQUESTS", str(concurrent_requests)))
    if concurrent_requests_per_domain is not None:
        setting_args.append(("CONCURRENT_REQUESTS_PER_DOMAIN", str(concurrent_requests_per_domain)))
    if autothrottle_target_concurrency is not None:
        setting_args.append(
            ("AUTOTHROTTLE_TARGET_CONCURRENCY", str(autothrottle_target_concurrency))
        )
    return setting_args


def _run_discovery(
    paths: RunPaths,
    crawl_run_id: str,
    *,
    crawl_setting_args: Sequence[tuple[str, str]],
) -> None:
    _run_scrapy_stage(
        spider_name="product_image_discovery",
        feed_path=paths.discovered_jsonl,
        jobdir_path=paths.discovery_jobdir,
        stats_path=paths.discovery_stats_json,
        spider_args=[
            ("seeds_file", str(paths.seeds_jsonl)),
            ("crawl_run_id", crawl_run_id),
        ],
        setting_args=crawl_setting_args,
    )


def _run_download(paths: RunPaths, *, crawl_setting_args: Sequence[tuple[str, str]]) -> None:
    _run_scrapy_stage(
        spider_name="product_image_download",
        feed_path=paths.downloads_jsonl,
        jobdir_path=paths.download_jobdir,
        stats_path=paths.download_stats_json,
        spider_args=[("manifest_file", str(paths.download_manifest_jsonl))],
        setting_args=[
            *crawl_setting_args,
            ("FILES_STORE", str(paths.output_root / "images")),
            ("FILES_EXPIRES", "3650"),
        ],
    )


def _run_crawl(
    *,
    limit: int | None,
    run_id: str,
    output_root_override: str | None,
    countries: Sequence[str] | None,
    skip_seen_pages: bool,
    concurrent_requests: int | None,
    concurrent_requests_per_domain: int | None,
    autothrottle_target_concurrency: float | None,
) -> RunPaths:
    repo_root = _repo_root()
    output_root = resolve_output_root(output_root_override)
    paths = build_run_paths(output_root, run_id)
    seen_source_page_urls = (
        _seen_source_page_urls(output_root, exclude_run_id=run_id) if skip_seen_pages else set()
    )
    seeds = load_product_seeds(
        repo_root=repo_root,
        limit=limit,
        countries=countries,
        skip_source_page_urls=seen_source_page_urls,
    )
    _write_seeds(paths, seeds)
    crawl_setting_args = _crawl_setting_args(
        concurrent_requests=concurrent_requests,
        concurrent_requests_per_domain=concurrent_requests_per_domain,
        autothrottle_target_concurrency=autothrottle_target_concurrency,
    )
    _run_discovery(paths, run_id, crawl_setting_args=crawl_setting_args)
    discovery_records = [
        DiscoveryRecord.from_dict(row) for row in read_jsonl(paths.discovered_jsonl)
    ]

    cached_records, manifest_rows = _prepare_download_stage(paths, discovery_records)
    if manifest_rows:
        write_jsonl(paths.download_manifest_jsonl, [row.to_dict() for row in manifest_rows])
        _run_download(paths, crawl_setting_args=crawl_setting_args)
        new_download_records = [
            DownloadRecord.from_dict(row) for row in read_jsonl(paths.downloads_jsonl)
        ]
    else:
        write_jsonl(paths.download_manifest_jsonl, [])
        new_download_records = []
        write_jsonl(paths.downloads_jsonl, [])

    all_download_records = cached_records + new_download_records
    write_jsonl(paths.downloads_jsonl, [record.to_dict() for record in all_download_records])
    catalog_rows = _merge_catalog_rows(
        discovery_records=discovery_records,
        download_records=all_download_records,
    )
    write_jsonl(paths.catalog_jsonl, catalog_rows)
    _write_catalog_parquet(catalog_rows, paths)
    summary = _run_summary(
        crawl_run_id=run_id,
        seeds=seeds,
        discovery_records=discovery_records,
        download_records=all_download_records,
        discovery_stats=_load_stats(paths.discovery_stats_json),
        download_stats=_load_stats(paths.download_stats_json),
        paths=paths,
    )
    paths.run_summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return paths


def build_parser() -> argparse.ArgumentParser:
    """Build the sidecar CLI parser."""

    parser = argparse.ArgumentParser(description="IKEA product image catalog sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl_parser = subparsers.add_parser(
        "crawl", help="Run discovery and download for one sampled batch"
    )
    crawl_parser.add_argument("--limit", type=int)
    crawl_parser.add_argument("--all", action="store_true")
    crawl_parser.add_argument("--run-id", default=f"crawl-{_now_compact()}")
    crawl_parser.add_argument("--output-root")
    crawl_parser.add_argument("--country", action="append", dest="countries")
    crawl_parser.add_argument("--concurrent-requests", type=int)
    crawl_parser.add_argument("--concurrent-requests-per-domain", type=int)
    crawl_parser.add_argument("--autothrottle-target-concurrency", type=float)
    crawl_parser.add_argument(
        "--skip-seen-pages",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "crawl":
        if arguments.all and arguments.limit is not None:
            parser.error("--all cannot be combined with an explicit --limit")
        limit: int | None = None if arguments.all else (arguments.limit or 1000)
        paths = _run_crawl(
            limit=limit,
            run_id=arguments.run_id,
            output_root_override=arguments.output_root,
            countries=arguments.countries,
            skip_seen_pages=arguments.skip_seen_pages,
            concurrent_requests=arguments.concurrent_requests,
            concurrent_requests_per_domain=arguments.concurrent_requests_per_domain,
            autothrottle_target_concurrency=arguments.autothrottle_target_concurrency,
        )
        print(
            json.dumps(
                {
                    "catalog_jsonl": str(paths.catalog_jsonl),
                    "catalog_parquet": str(paths.catalog_parquet),
                    "run_root": str(paths.run_root),
                }
            )
        )
        return 0
    parser.error(f"unsupported command: {arguments.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
