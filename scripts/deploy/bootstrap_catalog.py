"""Bootstrap the deployment database with the canonical catalog seed inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.docker_deps.seed_postgres import seed_postgres_database

from ikea_agent.config import get_settings
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    """Run the canonical catalog/bootstrap seed flow for one target database."""

    parser = argparse.ArgumentParser(description="Bootstrap catalog data for deployment.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--image-catalog-root", default=None)
    parser.add_argument("--image-catalog-run-id", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    repo_root = Path(args.repo_root or _repo_root()).resolve()
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    image_catalog_root = Path(
        args.image_catalog_root or settings.ikea_image_catalog_root_dir
    ).expanduser()
    image_catalog_run_id = args.image_catalog_run_id or settings.ikea_image_catalog_run_id

    summary = seed_postgres_database(
        engine=create_database_engine(database_url),
        repo_root=repo_root,
        image_catalog_root=image_catalog_root,
        image_catalog_run_id=image_catalog_run_id,
        force=args.force,
    )
    print(json.dumps(summary.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
