"""Drop obsolete message archive persistence table.

Revision ID: 20260320_0008
Revises: 20260319_0007
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260320_0008"
down_revision: str | Sequence[str] | None = "20260319_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.drop_table("message_archives", schema=APP_SCHEMA)


def downgrade() -> None:
    """Recreate the dropped archive table."""

    op.create_table(
        "message_archives",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("archive_version", sa.Integer(), nullable=False),
        sa.Column("agui_input_messages_json", sa.Text(), nullable=True),
        sa.Column("agui_event_trace_json", sa.Text(), nullable=True),
        sa.Column("pydantic_all_messages_json", sa.Text(), nullable=True),
        sa.Column("pydantic_new_messages_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        schema=APP_SCHEMA,
    )
