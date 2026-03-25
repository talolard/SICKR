"""Write one machine-readable release manifest for deploy automation."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.deploy.release_manifest import create_release_manifest, write_release_manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write one deploy release manifest.")
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--git-tag", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--postgres-seed-version", required=True)
    parser.add_argument("--image-catalog-run-id", required=True)
    parser.add_argument("--ui-repository", required=True)
    parser.add_argument("--ui-digest", required=True)
    parser.add_argument("--backend-repository", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Write the validated release manifest to disk."""

    args = _parse_args()
    manifest = create_release_manifest(
        app_version=args.app_version,
        git_tag=args.git_tag,
        git_sha=args.git_sha,
        postgres_seed_version=args.postgres_seed_version,
        image_catalog_run_id=args.image_catalog_run_id,
        ui_repository=args.ui_repository,
        ui_digest=args.ui_digest,
        backend_repository=args.backend_repository,
        backend_digest=args.backend_digest,
    )
    write_release_manifest(args.output, manifest)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
