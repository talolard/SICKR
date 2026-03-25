"""Emit the pinned bootstrap inputs for one release commit as JSON."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.deploy.bootstrap_inputs import create_release_bootstrap_inputs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Describe release bootstrap inputs.")
    parser.add_argument("--repo-root", type=Path, default=_repo_root())
    parser.add_argument("--image-catalog-run-id", required=True)
    return parser.parse_args()


def main() -> int:
    """Print the validated release bootstrap inputs as one JSON object."""

    args = _parse_args()
    inputs = create_release_bootstrap_inputs(
        repo_root=args.repo_root.resolve(),
        image_catalog_run_id=args.image_catalog_run_id,
    )
    print(json.dumps(asdict(inputs), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
