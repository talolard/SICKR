"""Add users, projects, rooms, and thread room ownership.

Revision ID: 20260320_0009
Revises: 20260320_0008
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"
DEFAULT_DEV_USER_ID = "user-dev-default"
DEFAULT_DEV_PROJECT_ID = "project-dev-default"
DEFAULT_DEV_ROOM_ID = "room-dev-default"

# revision identifiers, used by Alembic.
revision: str = "20260320_0009"
down_revision: str | Sequence[str] | None = "20260320_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    users_table = sa.table(
        "users",
        sa.column("user_id", sa.String(length=64)),
        sa.column("external_key", sa.String(length=128)),
        sa.column("display_name", sa.String(length=256)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        schema=APP_SCHEMA,
    )
    projects_table = sa.table(
        "projects",
        sa.column("project_id", sa.String(length=64)),
        sa.column("user_id", sa.String(length=64)),
        sa.column("title", sa.String(length=512)),
        sa.column("status", sa.String(length=32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        schema=APP_SCHEMA,
    )
    rooms_table = sa.table(
        "rooms",
        sa.column("room_id", sa.String(length=64)),
        sa.column("project_id", sa.String(length=64)),
        sa.column("title", sa.String(length=512)),
        sa.column("room_type", sa.String(length=128)),
        sa.column("status", sa.String(length=32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        schema=APP_SCHEMA,
    )
    threads_table = sa.table(
        "threads",
        sa.column("room_id", sa.String(length=64)),
        schema=APP_SCHEMA,
    )

    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=64), primary_key=True),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_key", name="uq_users_external_key"),
        schema=APP_SCHEMA,
    )

    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [f"{APP_SCHEMA}.users.user_id"]),
        sa.UniqueConstraint("user_id", "title", name="uq_projects_user_title"),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"], schema=APP_SCHEMA)

    op.create_table(
        "rooms",
        sa.Column("room_id", sa.String(length=64), primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("room_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{APP_SCHEMA}.projects.project_id"]),
        sa.UniqueConstraint("project_id", "title", name="uq_rooms_project_title"),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_rooms_project_id", "rooms", ["project_id"], schema=APP_SCHEMA)

    op.drop_index("ix_threads_owner_id", table_name="threads", schema=APP_SCHEMA)
    op.add_column(
        "threads", sa.Column("room_id", sa.String(length=64), nullable=True), schema=APP_SCHEMA
    )

    bind = op.get_bind()
    now = bind.execute(sa.text("SELECT CURRENT_TIMESTAMP")).scalar_one()
    bind.execute(
        sa.insert(users_table),
        {
            "user_id": DEFAULT_DEV_USER_ID,
            "external_key": "dev-user",
            "display_name": "Tal",
            "created_at": now,
            "updated_at": now,
        },
    )
    bind.execute(
        sa.insert(projects_table),
        {
            "project_id": DEFAULT_DEV_PROJECT_ID,
            "user_id": DEFAULT_DEV_USER_ID,
            "title": "Default project",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    )
    bind.execute(
        sa.insert(rooms_table),
        {
            "room_id": DEFAULT_DEV_ROOM_ID,
            "project_id": DEFAULT_DEV_PROJECT_ID,
            "title": "Untitled room",
            "room_type": None,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    )
    bind.execute(
        sa.update(threads_table)
        .where(threads_table.c.room_id.is_(None))
        .values(room_id=DEFAULT_DEV_ROOM_ID)
    )

    op.alter_column("threads", "room_id", schema=APP_SCHEMA, nullable=False)
    op.create_foreign_key(
        "fk_threads_room_id",
        "threads",
        "rooms",
        ["room_id"],
        ["room_id"],
        source_schema=APP_SCHEMA,
        referent_schema=APP_SCHEMA,
    )
    op.create_index("ix_threads_room_id", "threads", ["room_id"], schema=APP_SCHEMA)
    op.drop_column("threads", "owner_id", schema=APP_SCHEMA)


def downgrade() -> None:
    """Revert schema changes."""

    op.add_column(
        "threads", sa.Column("owner_id", sa.String(length=128), nullable=True), schema=APP_SCHEMA
    )
    op.drop_index("ix_threads_room_id", table_name="threads", schema=APP_SCHEMA)
    op.drop_constraint("fk_threads_room_id", "threads", schema=APP_SCHEMA, type_="foreignkey")
    op.drop_column("threads", "room_id", schema=APP_SCHEMA)
    op.create_index("ix_threads_owner_id", "threads", ["owner_id"], schema=APP_SCHEMA)

    op.drop_index("ix_rooms_project_id", table_name="rooms", schema=APP_SCHEMA)
    op.drop_table("rooms", schema=APP_SCHEMA)
    op.drop_index("ix_projects_user_id", table_name="projects", schema=APP_SCHEMA)
    op.drop_table("projects", schema=APP_SCHEMA)
    op.drop_table("users", schema=APP_SCHEMA)
