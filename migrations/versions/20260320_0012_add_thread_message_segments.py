"""Add canonical thread message segments.

Revision ID: 20260320_0012
Revises: 20260320_0011
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260320_0012"
down_revision: str | Sequence[str] | None = "20260320_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.create_table(
        "thread_message_segments",
        sa.Column("thread_message_segment_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("messages_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            [f"{APP_SCHEMA}.threads.thread_id"],
            name="fk_thread_message_segments_thread_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            [f"{APP_SCHEMA}.agent_runs.run_id"],
            name="fk_thread_message_segments_run_id",
        ),
        sa.PrimaryKeyConstraint("thread_message_segment_id"),
        sa.UniqueConstraint("run_id", name="uq_thread_message_segments_run_id"),
        sa.UniqueConstraint(
            "thread_id",
            "sequence_no",
            name="uq_thread_message_segments_thread_sequence",
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_thread_message_segments_thread_id",
        "thread_message_segments",
        ["thread_id"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_index(
        "ix_thread_message_segments_thread_id",
        table_name="thread_message_segments",
        schema=APP_SCHEMA,
    )
    op.drop_table("thread_message_segments", schema=APP_SCHEMA)
