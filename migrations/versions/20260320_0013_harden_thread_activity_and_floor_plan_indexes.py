"""Harden thread activity and floor-plan revision indexes.

Revision ID: 20260320_0013
Revises: 20260320_0012
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260320_0013"
down_revision: str | Sequence[str] | None = "20260320_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.drop_index("ix_threads_room_id", table_name="threads", schema=APP_SCHEMA)
    op.drop_index(
        "ix_threads_last_activity_at",
        table_name="threads",
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_threads_room_activity",
        "threads",
        ["room_id", "last_activity_at", "updated_at"],
        schema=APP_SCHEMA,
    )

    op.drop_index(
        "ix_floor_plan_revisions_room_id",
        table_name="floor_plan_revisions",
        schema=APP_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_floor_plan_revisions_room_revision",
        "floor_plan_revisions",
        ["room_id", "revision"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_constraint(
        "uq_floor_plan_revisions_room_revision",
        "floor_plan_revisions",
        schema=APP_SCHEMA,
        type_="unique",
    )
    op.create_index(
        "ix_floor_plan_revisions_room_id",
        "floor_plan_revisions",
        ["room_id"],
        schema=APP_SCHEMA,
    )

    op.drop_index(
        "ix_threads_room_activity",
        table_name="threads",
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_threads_last_activity_at", "threads", ["last_activity_at"], schema=APP_SCHEMA
    )
    op.create_index("ix_threads_room_id", "threads", ["room_id"], schema=APP_SCHEMA)
