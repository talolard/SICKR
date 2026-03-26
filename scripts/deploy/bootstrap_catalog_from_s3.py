"""Bootstrap deploy catalog state from artifacts staged in S3.

The deployed Aurora cluster is private to the VPC, so the bootstrap seed step
must run inside ECS rather than from Tal's laptop or a GitHub-hosted runner.
This module downloads the pinned parquet and image-catalog artifacts into a
temporary filesystem layout that matches the normal seed helpers, then runs the
existing `seed_postgres_database` flow against the live database.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from logging import getLogger
from pathlib import Path, PurePosixPath

import boto3

from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url
from scripts.docker_deps.seed_postgres import seed_postgres_database

logger = getLogger(__name__)


def main() -> None:
    """Download one pinned bootstrap payload from S3 and seed the live database."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-bucket", required=True)
    parser.add_argument("--artifacts-prefix", required=True)
    parser.add_argument("--image-catalog-object-name", required=True)
    parser.add_argument("--image-catalog-run-id", required=True)
    parser.add_argument("--product-image-base-url", required=True)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--aws-region", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    s3 = boto3.client("s3", region_name=args.aws_region or settings.artifact_s3_region)

    with tempfile.TemporaryDirectory(prefix="ikea-bootstrap-") as temp_dir:
        repo_root = Path(temp_dir) / "repo"
        image_catalog_root = Path(temp_dir) / "ikea_image_catalog"
        run_dir = image_catalog_root / "runs" / args.image_catalog_run_id
        parquet_dir = repo_root / "data" / "parquet"
        parquet_dir.mkdir(parents=True, exist_ok=True)
        run_dir.mkdir(parents=True, exist_ok=True)

        _download_object(
            s3_client=s3,
            bucket=args.artifacts_bucket,
            key=f"{args.artifacts_prefix.rstrip('/')}/product_embeddings",
            destination=parquet_dir / "product_embeddings",
        )
        _download_prefix(
            s3_client=s3,
            bucket=args.artifacts_bucket,
            prefix=f"{args.artifacts_prefix.rstrip('/')}/products_canonical/",
            destination=parquet_dir / "products_canonical",
        )
        _download_object(
            s3_client=s3,
            bucket=args.artifacts_bucket,
            key=f"{args.artifacts_prefix.rstrip('/')}/{args.image_catalog_object_name}",
            destination=run_dir / args.image_catalog_object_name,
        )

        logger.info(
            "deployment_bootstrap_from_s3_start",
            extra={
                "artifacts_bucket": args.artifacts_bucket,
                "artifacts_prefix": args.artifacts_prefix,
                "image_catalog_run_id": args.image_catalog_run_id,
                "release_version": settings.release_version,
            },
        )
        summary = seed_postgres_database(
            engine=create_database_engine(
                database_url,
                pool_mode=settings.database_pool_mode,
            ),
            repo_root=repo_root,
            image_catalog_root=image_catalog_root,
            image_catalog_run_id=args.image_catalog_run_id,
            product_image_base_url=args.product_image_base_url,
            force=args.force,
        )
        logger.info(
            "deployment_bootstrap_from_s3_complete",
            extra={
                "artifacts_bucket": args.artifacts_bucket,
                "artifacts_prefix": args.artifacts_prefix,
                "image_catalog_run_id": args.image_catalog_run_id,
                "release_version": settings.release_version,
                "skipped": summary.skipped,
            },
        )
        print(json.dumps(asdict(summary), sort_keys=True))


def _download_object(*, s3_client: object, bucket: str, key: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket, key, str(destination))


def _download_prefix(*, s3_client: object, bucket: str, prefix: str, destination: Path) -> None:
    normalized_prefix = prefix.rstrip("/") + "/"
    destination.mkdir(parents=True, exist_ok=True)
    paginator = s3_client.get_paginator("list_objects_v2")
    downloaded_any = False
    for page in paginator.paginate(Bucket=bucket, Prefix=normalized_prefix):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if not isinstance(key, str) or not key.startswith(normalized_prefix):
                continue
            relative_path = PurePosixPath(key).relative_to(PurePosixPath(normalized_prefix))
            if not relative_path.parts:
                continue
            _download_object(
                s3_client=s3_client,
                bucket=bucket,
                key=key,
                destination=destination.joinpath(*relative_path.parts),
            )
            downloaded_any = True
    if not downloaded_any:
        msg = f"No S3 objects found under prefix s3://{bucket}/{normalized_prefix}"
        raise FileNotFoundError(msg)


if __name__ == "__main__":
    main()
