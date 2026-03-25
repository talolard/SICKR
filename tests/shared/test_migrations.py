from __future__ import annotations

import psycopg
import pytest
from alembic import command
from scripts.deploy.migration_test_support import (
    resolve_postgres_test_environment,
    temporary_postgres_database,
)
from sqlalchemy import create_engine

from ikea_agent.persistence.models import ensure_persistence_schema


def test_alembic_upgrade_creates_runtime_tables() -> None:
    environment = resolve_postgres_test_environment()
    if environment is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")
    try:
        with temporary_postgres_database(environment, prefix="alembic_test") as database:
            cfg = database.alembic_config()
            command.upgrade(cfg, "head")

            with (
                psycopg.connect(database.connect_url) as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('app', 'catalog', 'ops')
                    ORDER BY table_schema, table_name
                    """
                )
                table_names = {(str(row[0]), str(row[1])) for row in cursor.fetchall()}
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")
    assert {
        ("app", "threads"),
        ("app", "agent_runs"),
        ("app", "assets"),
        ("app", "floor_plan_revisions"),
        ("app", "analysis_runs"),
        ("app", "analysis_input_assets"),
        ("app", "analysis_detections"),
        ("app", "search_runs"),
        ("app", "search_results"),
        ("app", "revealed_preferences"),
        ("app", "room_3d_assets"),
        ("app", "room_3d_snapshots"),
        ("catalog", "products_canonical"),
        ("catalog", "product_embeddings"),
        ("catalog", "product_embedding_neighbors"),
        ("catalog", "product_images"),
        ("ops", "seed_state"),
    }.issubset(table_names)
    assert ("app", "message_archives") not in table_names


def test_alembic_upgrade_succeeds_when_revealed_preferences_already_exists() -> None:
    environment = resolve_postgres_test_environment()
    if environment is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")
    try:
        with temporary_postgres_database(environment, prefix="alembic_test") as database:
            cfg = database.alembic_config()
            command.upgrade(cfg, "20260320_0013")
            engine = create_engine(database.sqlalchemy_url, future=True)
            ensure_persistence_schema(engine)
            engine.dispose()

            command.upgrade(cfg, "head")

            with (
                psycopg.connect(database.connect_url) as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'app'
                      AND table_name = 'revealed_preferences'
                    """
                )
                row = cursor.fetchone()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")
    assert row == (1,)
