"""Verify that the required deployment seed-state rows are present and ready."""

from __future__ import annotations

import argparse
import json
from logging import getLogger

from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.deploy_readiness import REQUIRED_SEED_SYSTEMS, collect_seed_verification
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url

logger = getLogger(__name__)


def main() -> None:
    """Check that deploy-ready seed state and seeded catalog data are usable."""

    parser = argparse.ArgumentParser(description="Verify deployment seed-state readiness.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--expected-postgres-seed-version", default=None)
    parser.add_argument("--expected-image-catalog-seed-version", default=None)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    logger.info(
        "deployment_seed_state_check_start",
        extra={
            "environment": settings.runtime_environment,
            "release_version": settings.release_version,
        },
    )
    engine = create_database_engine(
        database_url,
        pool_mode=settings.database_pool_mode,
    )
    verification = collect_seed_verification(
        engine,
        image_serving_strategy=settings.image_serving_strategy,
    )
    systems = verification.details.systems
    missing = [system_name for system_name in REQUIRED_SEED_SYSTEMS if system_name not in systems]
    unready = [
        system_name
        for system_name in REQUIRED_SEED_SYSTEMS
        if systems.get(system_name, {}).get("status") != "ready"
    ]
    version_mismatches: list[str] = []
    expected_versions = {
        POSTGRES_SEED_SYSTEM: args.expected_postgres_seed_version,
        IMAGE_CATALOG_SEED_SYSTEM: args.expected_image_catalog_seed_version,
    }
    for system_name, expected_version in expected_versions.items():
        if expected_version is None:
            continue
        actual_version = systems.get(system_name, {}).get("version")
        if actual_version != expected_version:
            version_mismatches.append(system_name)
    payload = {
        "status": (
            "ok"
            if (
                verification.seed_state.status == "ok"
                and verification.catalog_data.status == "ok"
                and not version_mismatches
            )
            else "not_ready"
        ),
        "required_seed_systems": list(REQUIRED_SEED_SYSTEMS),
        "image_serving_strategy": settings.image_serving_strategy,
        "checks": {
            "seed_state": {
                "status": verification.seed_state.status,
                "detail": verification.seed_state.detail,
            },
            "catalog_data": {
                "status": verification.catalog_data.status,
                "detail": verification.catalog_data.detail,
            },
        },
        "systems": systems,
        "table_counts": verification.details.table_counts,
        "missing_public_image_urls": verification.details.missing_public_image_urls,
        "missing": missing,
        "unready": unready,
        "expected_versions": {
            key: value for key, value in expected_versions.items() if value is not None
        },
        "version_mismatches": version_mismatches,
    }
    logger.info(
        "deployment_seed_state_check_complete",
        extra={
            "environment": settings.runtime_environment,
            "missing": missing,
            "release_version": settings.release_version,
            "status": payload["status"],
            "unready": unready,
        },
    )
    print(json.dumps(payload, sort_keys=True))
    if payload["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
