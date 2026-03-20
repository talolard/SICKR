"""Add room ownership to durable artifact tables.

Revision ID: 20260320_0011
Revises: 20260320_0010
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260320_0011"
down_revision: str | Sequence[str] | None = "20260320_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROOM_OWNED_TABLES: tuple[tuple[str, str, str], ...] = (
    ("assets", "fk_assets_room_id", "ix_assets_room_id"),
    ("floor_plan_revisions", "fk_floor_plan_revisions_room_id", "ix_floor_plan_revisions_room_id"),
    ("room_3d_assets", "fk_room_3d_assets_room_id", "ix_room_3d_assets_room_id"),
    ("room_3d_snapshots", "fk_room_3d_snapshots_room_id", "ix_room_3d_snapshots_room_id"),
    ("analysis_runs", "fk_analysis_runs_room_id", "ix_analysis_runs_room_id"),
    ("analysis_feedback", "fk_analysis_feedback_room_id", "ix_analysis_feedback_room_id"),
    ("search_runs", "fk_search_runs_room_id", "ix_search_runs_room_id"),
    ("bundle_proposals", "fk_bundle_proposals_room_id", "ix_bundle_proposals_room_id"),
)


def _backfill_room_ids(table_name: str) -> None:
    bind = op.get_bind()
    artifact_table = sa.table(
        table_name,
        sa.column("thread_id", sa.String(length=64)),
        sa.column("room_id", sa.String(length=64)),
        schema=APP_SCHEMA,
    )
    thread_table = sa.table(
        "threads",
        sa.column("thread_id", sa.String(length=64)),
        sa.column("room_id", sa.String(length=64)),
        schema=APP_SCHEMA,
    )
    room_id_subquery = (
        sa.select(thread_table.c.room_id)
        .where(thread_table.c.thread_id == artifact_table.c.thread_id)
        .scalar_subquery()
    )
    bind.execute(
        sa.update(artifact_table)
        .values(room_id=room_id_subquery)
        .where(
            sa.exists(sa.select(1).where(thread_table.c.thread_id == artifact_table.c.thread_id))
        )
    )


def upgrade() -> None:
    """Apply schema changes."""

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names(schema=APP_SCHEMA))
    for table_name, fk_name, index_name in _ROOM_OWNED_TABLES:
        if table_name not in existing_tables:
            continue
        op.add_column(
            table_name,
            sa.Column("room_id", sa.String(length=64), nullable=True),
            schema=APP_SCHEMA,
        )
        _backfill_room_ids(table_name)
        op.alter_column(table_name, "room_id", nullable=False, schema=APP_SCHEMA)
        op.create_foreign_key(
            fk_name,
            table_name,
            "rooms",
            ["room_id"],
            ["room_id"],
            source_schema=APP_SCHEMA,
            referent_schema=APP_SCHEMA,
        )
        op.create_index(index_name, table_name, ["room_id"], schema=APP_SCHEMA)


def downgrade() -> None:
    """Revert schema changes."""

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names(schema=APP_SCHEMA))
    for table_name, fk_name, index_name in reversed(_ROOM_OWNED_TABLES):
        if table_name not in existing_tables:
            continue
        op.drop_index(index_name, table_name=table_name, schema=APP_SCHEMA)
        op.drop_constraint(fk_name, table_name, schema=APP_SCHEMA, type_="foreignkey")
        op.drop_column(table_name, "room_id", schema=APP_SCHEMA)
