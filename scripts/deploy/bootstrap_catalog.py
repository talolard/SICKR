"""Bootstrap the deployment database with the canonical catalog seed inputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from logging import getLogger
from pathlib import Path

from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url
from scripts.docker_deps.seed_postgres import seed_postgres_database

logger = getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    """Run the canonical catalog/bootstrap seed flow for one target database."""

    parser = argparse.ArgumentParser(description="Bootstrap catalog data for deployment.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--image-catalog-root", default=None)
    parser.add_argument("--image-catalog-run-id", default=None)
    parser.add_argument("--product-image-base-url", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    repo_root = Path(args.repo_root or _repo_root()).resolve()
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    image_catalog_root = Path(
        args.image_catalog_root or settings.ikea_image_catalog_root_dir
    ).expanduser()
    image_catalog_run_id = args.image_catalog_run_id or settings.ikea_image_catalog_run_id
    product_image_base_url = args.product_image_base_url or settings.image_service_base_url

    logger.info(
        "deployment_seed_verification_start",
        extra={
            "environment": settings.runtime_environment,
            "force_refresh": args.force,
            "release_version": settings.release_version,
        },
    )
    try:
        summary = seed_postgres_database(
            engine=create_database_engine(
                database_url,
                pool_mode=settings.database_pool_mode,
            ),
            repo_root=repo_root,
            image_catalog_root=image_catalog_root,
            image_catalog_run_id=image_catalog_run_id,
            product_image_base_url=product_image_base_url,
            force=args.force,
        )
    except Exception:
        logger.exception(
            "deployment_seed_verification_failed",
            extra={
                "environment": settings.runtime_environment,
                "force_refresh": args.force,
                "release_version": settings.release_version,
            },
        )
        raise
    logger.info(
        "deployment_seed_verification_succeeded",
        extra={
            "environment": settings.runtime_environment,
            "force_refresh": args.force,
            "release_version": settings.release_version,
            "skipped": summary.skipped,
        },
    )
    print(json.dumps(asdict(summary), sort_keys=True))


if __name__ == "__main__":
    main()
