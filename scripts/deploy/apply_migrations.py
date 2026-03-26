"""Run Alembic migrations for the configured deployment database."""

from __future__ import annotations

import argparse
import json
from logging import getLogger
from pathlib import Path

from alembic import command
from alembic.config import Config

from ikea_agent.config import get_settings
from ikea_agent.logging_config import configure_logging
from ikea_agent.observability.logfire_setup import configure_logfire
from ikea_agent.shared.deploy_readiness import collect_runtime_schema_verification
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url
from scripts.deploy.alembic_config import set_sqlalchemy_url

logger = getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(_repo_root() / "alembic.ini"))
    set_sqlalchemy_url(config, database_url)
    return config


def main() -> None:
    """Apply all pending Alembic revisions and print the resulting revision."""

    parser = argparse.ArgumentParser(description="Apply runtime Alembic migrations.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level_name=settings.log_level, json_logs=settings.log_json)
    configure_logfire(settings)
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    alembic_config = _alembic_config(database_url=database_url)
    logger.info(
        "deployment_migration_start",
        extra={
            "environment": settings.runtime_environment,
            "release_version": settings.release_version,
        },
    )
    try:
        command.upgrade(alembic_config, "head")

        engine = create_database_engine(
            database_url,
            pool_mode=settings.database_pool_mode,
        )
        schema_verification = collect_runtime_schema_verification(
            engine,
            alembic_config=alembic_config,
        )
    except Exception:
        logger.exception(
            "deployment_migration_failed",
            extra={
                "environment": settings.runtime_environment,
                "release_version": settings.release_version,
            },
        )
        raise

    if schema_verification.schema.status != "ok":
        logger.error(
            "deployment_migration_schema_verification_failed",
            extra={
                "current_revision": schema_verification.details.current_revision,
                "environment": settings.runtime_environment,
                "head_revision": schema_verification.details.head_revision,
                "missing_tables": list(schema_verification.details.missing_tables),
                "release_version": settings.release_version,
            },
        )
        raise RuntimeError(schema_verification.schema.detail)

    logger.info(
        "deployment_migration_succeeded",
        extra={
            "current_revision": schema_verification.details.current_revision,
            "environment": settings.runtime_environment,
            "head_revision": schema_verification.details.head_revision,
            "missing_tables": list(schema_verification.details.missing_tables),
            "release_version": settings.release_version,
        },
    )
    print(
        json.dumps(
            {
                "current_revision": schema_verification.details.current_revision,
                "head_revision": schema_verification.details.head_revision,
                "missing_tables": list(schema_verification.details.missing_tables),
                "status": "ok",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
