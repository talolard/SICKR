"""Path configuration for the sidecar's shared output root and per-run files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_ROOT = Path("/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog")
OUTPUT_ROOT_ENV_VAR = "IKEA_IMAGE_CATALOG_OUTPUT_ROOT"


@dataclass(slots=True)
class RunPaths:
    """Resolved paths for one sidecar run."""

    output_root: Path
    images_root: Path
    run_root: Path
    seeds_jsonl: Path
    discovered_jsonl: Path
    download_manifest_jsonl: Path
    downloads_jsonl: Path
    catalog_jsonl: Path
    catalog_parquet: Path
    run_summary_json: Path
    discovery_stats_json: Path
    download_stats_json: Path
    discovery_jobdir: Path
    download_jobdir: Path


def resolve_output_root(override: str | None = None) -> Path:
    """Resolve the shared output root, honoring an explicit override first."""

    raw = override or os.environ.get(OUTPUT_ROOT_ENV_VAR)
    if raw is None:
        return DEFAULT_OUTPUT_ROOT
    return Path(raw).expanduser().resolve()


def build_run_paths(output_root: Path, run_id: str) -> RunPaths:
    """Build and create the per-run path bundle."""

    resolved_root = output_root.expanduser().resolve()
    images_root = resolved_root / "images" / "masters"
    run_root = resolved_root / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    images_root.mkdir(parents=True, exist_ok=True)
    return RunPaths(
        output_root=resolved_root,
        images_root=images_root,
        run_root=run_root,
        seeds_jsonl=run_root / "seed_products.jsonl",
        discovered_jsonl=run_root / "discovered.jsonl",
        download_manifest_jsonl=run_root / "download_manifest.jsonl",
        downloads_jsonl=run_root / "downloads.jsonl",
        catalog_jsonl=run_root / "catalog.jsonl",
        catalog_parquet=run_root / "catalog.parquet",
        run_summary_json=run_root / "run_summary.json",
        discovery_stats_json=run_root / "discovery_stats.json",
        download_stats_json=run_root / "download_stats.json",
        discovery_jobdir=run_root / "jobdir-discovery",
        download_jobdir=run_root / "jobdir-download",
    )


def local_image_path(images_root: Path, image_asset_key: str) -> Path:
    """Resolve the stable on-disk location for one canonical asset key."""

    return images_root / image_asset_key
