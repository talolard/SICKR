from __future__ import annotations

import psycopg
import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from psycopg.errors import ObjectInUse
from scripts.deploy.migration_test_support import (
    database_has_catalog_seed_data,
    ordered_revision_chain,
    resolve_postgres_test_environment,
    temporary_postgres_database,
)
from sqlalchemy import create_engine


def test_alembic_stairway_round_trips_every_revision() -> None:
    environment = resolve_postgres_test_environment()
    if environment is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")

    try:
        with temporary_postgres_database(environment, prefix="alembic_stairway") as database:
            config = database.alembic_config()
            revision_chain = ordered_revision_chain(config)

            for revision, down_revision in revision_chain:
                command.upgrade(config, revision)
                _assert_current_revision(database.sqlalchemy_url, revision)
                command.downgrade(config, down_revision or "base")
                command.upgrade(config, revision)
                _assert_current_revision(database.sqlalchemy_url, revision)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")


def test_latest_revision_round_trips_from_fixture_seeded_template() -> None:
    environment = resolve_postgres_test_environment()
    if environment is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")

    try:
        if not database_has_catalog_seed_data(connect_url=environment.base_connect_url):
            pytest.skip(
                "Fixture-seeded catalog data is not available for populated migration tests."
            )

        with temporary_postgres_database(
            environment,
            prefix="alembic_populated",
            template_database=environment.base_database_name,
        ) as database:
            config = database.alembic_config()
            revision_chain = ordered_revision_chain(config)
            head_revision, previous_revision = revision_chain[-1]
            assert previous_revision is not None
            command.downgrade(config, previous_revision)
            command.upgrade(config, head_revision)
            _assert_current_revision(database.sqlalchemy_url, head_revision)
            assert database_has_catalog_seed_data(connect_url=database.connect_url)
    except ObjectInUse as exc:
        pytest.skip(f"Seeded template database is in use and cannot be cloned safely: {exc}")
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")


def _assert_current_revision(database_url: str, expected_revision: str) -> None:
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            current_revision = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()

    assert current_revision == expected_revision
