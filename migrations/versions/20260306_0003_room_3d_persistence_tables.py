"""Add room 3D asset and snapshot persistence tables.

Revision ID: 20260306_0003
Revises: 20260306_0002
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260306_0003"
down_revision: str | Sequence[str] | None = "20260306_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.create_table(
        "room_3d_assets",
        sa.Column("room_3d_asset_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("source_asset_id", sa.String(length=64), nullable=False),
        sa.Column("usd_format", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.ForeignKeyConstraint(["source_asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_room_3d_assets_thread_id",
        "room_3d_assets",
        ["thread_id"],
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_room_3d_assets_source_asset_id",
        "room_3d_assets",
        ["source_asset_id"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "room_3d_snapshots",
        sa.Column("room_3d_snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_asset_id", sa.String(length=64), nullable=False),
        sa.Column("room_3d_asset_id", sa.String(length=64), nullable=True),
        sa.Column("camera_json", sa.Text(), nullable=False),
        sa.Column("lighting_json", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.ForeignKeyConstraint(["snapshot_asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        sa.ForeignKeyConstraint(["room_3d_asset_id"], [f"{APP_SCHEMA}.room_3d_assets.room_3d_asset_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_room_3d_snapshots_thread_id",
        "room_3d_snapshots",
        ["thread_id"],
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_room_3d_snapshots_snapshot_asset_id",
        "room_3d_snapshots",
        ["snapshot_asset_id"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_index(
        "ix_room_3d_snapshots_snapshot_asset_id",
        table_name="room_3d_snapshots",
        schema=APP_SCHEMA,
    )
    op.drop_index(
        "ix_room_3d_snapshots_thread_id",
        table_name="room_3d_snapshots",
        schema=APP_SCHEMA,
    )
    op.drop_table("room_3d_snapshots", schema=APP_SCHEMA)

    op.drop_index(
        "ix_room_3d_assets_source_asset_id",
        table_name="room_3d_assets",
        schema=APP_SCHEMA,
    )
    op.drop_index(
        "ix_room_3d_assets_thread_id",
        table_name="room_3d_assets",
        schema=APP_SCHEMA,
    )
    op.drop_table("room_3d_assets", schema=APP_SCHEMA)
