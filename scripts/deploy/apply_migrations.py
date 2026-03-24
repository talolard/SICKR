"""Run Alembic migrations for the configured deployment database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from ikea_agent.config import get_settings
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(_repo_root() / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def main() -> None:
    """Apply all pending Alembic revisions and print the resulting revision."""

    parser = argparse.ArgumentParser(description="Apply runtime Alembic migrations.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    settings = get_settings()
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    alembic_config = _alembic_config(database_url=database_url)
    command.upgrade(alembic_config, "head")

    engine = create_database_engine(database_url)
    with engine.connect() as connection:
        revision = MigrationContext.configure(connection).get_current_revision()

    print(json.dumps({"status": "ok", "current_revision": revision}, sort_keys=True))


if __name__ == "__main__":
    main()
