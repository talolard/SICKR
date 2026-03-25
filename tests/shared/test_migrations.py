from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from scripts.deploy.alembic_config import set_sqlalchemy_url
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from ikea_agent.persistence.models import ensure_persistence_schema


def _postgres_test_urls() -> tuple[str, str, str] | None:
    configured_url = (
        os.getenv("ALEMBIC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or _database_url_from_worktree_env()
    )
    if not configured_url:
        return None
    sqlalchemy_url = make_url(configured_url)
    if not sqlalchemy_url.drivername.startswith("postgresql"):
        return None
    database_name = f"alembic_test_{uuid4().hex[:10]}"
    admin_url = sqlalchemy_url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    target_url = sqlalchemy_url.set(database=database_name).render_as_string(hide_password=False)
    psycopg_target_url = sqlalchemy_url.set(
        drivername="postgresql",
        database=database_name,
    ).render_as_string(hide_password=False)
    return admin_url, target_url, psycopg_target_url


def _database_url_from_worktree_env() -> str | None:
    env_path = Path(".tmp_untracked/worktree.env")
    if not env_path.exists():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("export DATABASE_URL="):
            return line.removeprefix("export DATABASE_URL=").strip()
    return None


def test_alembic_upgrade_creates_runtime_tables() -> None:
    urls = _postgres_test_urls()
    if urls is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")
    admin_url, target_url, psycopg_target_url = urls
    database_name = make_url(target_url).database
    assert database_name is not None

    try:
        with (
            closing(psycopg.connect(admin_url, autocommit=True)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")

    cfg = Config("alembic.ini")
    set_sqlalchemy_url(cfg, target_url)
    cfg.set_main_option("script_location", "migrations")

    try:
        command.upgrade(cfg, "head")

        with (
            closing(psycopg.connect(psycopg_target_url)) as connection,
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

        assert {
            ("app", "users"),
            ("app", "projects"),
            ("app", "rooms"),
            ("app", "threads"),
            ("app", "agent_runs"),
            ("app", "thread_message_segments"),
            ("app", "assets"),
            ("app", "floor_plan_revisions"),
            ("app", "analysis_runs"),
            ("app", "analysis_input_assets"),
            ("app", "analysis_detections"),
            ("app", "room_facts"),
            ("app", "project_facts"),
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
    finally:
        with (
            closing(psycopg.connect(admin_url, autocommit=True)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
            )


def test_alembic_upgrade_succeeds_when_revealed_preferences_already_exists() -> None:
    urls = _postgres_test_urls()
    if urls is None:
        pytest.skip("Postgres DATABASE_URL is not configured for migration validation.")
    admin_url, target_url, psycopg_target_url = urls
    database_name = make_url(target_url).database
    assert database_name is not None

    try:
        with (
            closing(psycopg.connect(admin_url, autocommit=True)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is not reachable for migration validation: {exc}")

    cfg = Config("alembic.ini")
    set_sqlalchemy_url(cfg, target_url)
    cfg.set_main_option("script_location", "migrations")

    try:
        command.upgrade(cfg, "20260319_0007")
        engine = create_engine(target_url, future=True)
        ensure_persistence_schema(engine)
        engine.dispose()

        command.upgrade(cfg, "head")

        with (
            closing(psycopg.connect(psycopg_target_url)) as connection,
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
            assert cursor.fetchone() == (1,)
    finally:
        with (
            closing(psycopg.connect(admin_url, autocommit=True)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
            )
