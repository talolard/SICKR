"""Shared helpers for migration validation tests.

These helpers deliberately live next to the deploy migration entrypoints because
the tests should exercise the same Alembic configuration path that release and
deploy automation use.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import psycopg
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy.engine import make_url

from scripts.deploy.alembic_config import set_sqlalchemy_url


@dataclass(frozen=True, slots=True)
class PostgresTestEnvironment:
    """Connection details for creating isolated migration test databases."""

    admin_url: str
    base_connect_url: str
    base_database_name: str
    base_sqlalchemy_url: str


@dataclass(frozen=True, slots=True)
class PostgresTestDatabase:
    """One ephemeral database reserved for a single migration test."""

    admin_url: str
    connect_url: str
    database_name: str
    sqlalchemy_url: str

    def alembic_config(self) -> Config:
        """Build an Alembic config that targets this database."""

        config = Config("alembic.ini")
        set_sqlalchemy_url(config, self.sqlalchemy_url)
        config.set_main_option("script_location", "migrations")
        return config


def resolve_postgres_test_environment() -> PostgresTestEnvironment | None:
    """Resolve the configured Postgres target for migration tests.

    The lookup order matches the existing migration tests:
    explicit Alembic override, normal runtime database URL, then the
    worktree-local environment file.
    """

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
    database_name = sqlalchemy_url.database
    if not database_name:
        return None
    admin_url = sqlalchemy_url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    connect_url = sqlalchemy_url.set(drivername="postgresql").render_as_string(hide_password=False)
    sqlalchemy_database_url = sqlalchemy_url.render_as_string(hide_password=False)
    return PostgresTestEnvironment(
        admin_url=admin_url,
        base_connect_url=connect_url,
        base_database_name=database_name,
        base_sqlalchemy_url=sqlalchemy_database_url,
    )


@contextmanager
def temporary_postgres_database(
    environment: PostgresTestEnvironment,
    *,
    prefix: str,
    template_database: str | None = None,
) -> Generator[PostgresTestDatabase]:
    """Create a throwaway Postgres database and drop it after the test."""

    database_name = f"{prefix}_{uuid4().hex[:10]}"
    sqlalchemy_url = make_url(environment.base_sqlalchemy_url).set(database=database_name)
    target_sqlalchemy_url = sqlalchemy_url.render_as_string(hide_password=False)
    target_connect_url = sqlalchemy_url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    create_database(
        admin_url=environment.admin_url,
        database_name=database_name,
        template_database=template_database,
    )
    try:
        yield PostgresTestDatabase(
            admin_url=environment.admin_url,
            connect_url=target_connect_url,
            database_name=database_name,
            sqlalchemy_url=target_sqlalchemy_url,
        )
    finally:
        drop_database(admin_url=environment.admin_url, database_name=database_name)


def create_database(
    *,
    admin_url: str,
    database_name: str,
    template_database: str | None = None,
) -> None:
    """Create one empty or template-cloned Postgres database."""

    statement = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
    if template_database is not None:
        statement += sql.SQL(" TEMPLATE {}").format(sql.Identifier(template_database))
    with (
        psycopg.connect(admin_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(statement)


def drop_database(*, admin_url: str, database_name: str) -> None:
    """Terminate connections and drop one throwaway Postgres database."""

    with (
        psycopg.connect(admin_url, autocommit=True) as connection,
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
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))


def ordered_revision_chain(config: Config) -> list[tuple[str, str | None]]:
    """Return the repo's Alembic revisions in forward order for stairway tests."""

    script_directory = ScriptDirectory.from_config(config)
    head_revisions = script_directory.get_heads()
    if len(head_revisions) != 1:
        msg = f"Expected one linear Alembic head, found {head_revisions!r}."
        raise ValueError(msg)
    revisions = list(reversed(list(script_directory.walk_revisions(base="base", head="heads"))))
    return [
        (revision.revision, _single_down_revision(revision.down_revision)) for revision in revisions
    ]


def database_has_catalog_seed_data(*, connect_url: str) -> bool:
    """Return whether the candidate template database looks seeded with catalog data."""

    try:
        with (
            psycopg.connect(connect_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SELECT count(*) FROM catalog.products_canonical")
            row = cursor.fetchone()
    except psycopg.Error:
        return False
    return row is not None and int(row[0]) > 0


def _single_down_revision(
    down_revision: str | list[str] | tuple[str, ...] | None,
) -> str | None:
    """Normalize Alembic down-revision metadata to one linear token."""

    if down_revision is None:
        return None
    if isinstance(down_revision, tuple | list):
        if len(down_revision) != 1:
            msg = f"Expected one down_revision per migration, found {down_revision!r}."
            raise ValueError(msg)
        return down_revision[0]
    return down_revision


def _database_url_from_worktree_env() -> str | None:
    env_path = Path(".tmp_untracked/worktree.env")
    if not env_path.exists():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("export DATABASE_URL="):
            return line.removeprefix("export DATABASE_URL=").strip()
    return None
