"""Replace thread-scoped revealed preferences with room and project facts.

Revision ID: 20260320_0010
Revises: 20260320_0009
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260320_0010"
down_revision: str | Sequence[str] | None = "20260320_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.create_table(
        "room_facts",
        sa.Column("room_fact_id", sa.String(length=64), primary_key=True),
        sa.Column("room_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("signal_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], [f"{APP_SCHEMA}.rooms.room_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.UniqueConstraint(
            "room_id", "signal_key", "value", name="uq_room_facts_room_signal_value"
        ),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_room_facts_room_id", "room_facts", ["room_id"], schema=APP_SCHEMA)
    op.create_index("ix_room_facts_run_id", "room_facts", ["run_id"], schema=APP_SCHEMA)

    op.create_table(
        "project_facts",
        sa.Column("project_fact_id", sa.String(length=64), primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("signal_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{APP_SCHEMA}.projects.project_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.UniqueConstraint(
            "project_id",
            "signal_key",
            "value",
            name="uq_project_facts_project_signal_value",
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_project_facts_project_id",
        "project_facts",
        ["project_id"],
        schema=APP_SCHEMA,
    )
    op.create_index("ix_project_facts_run_id", "project_facts", ["run_id"], schema=APP_SCHEMA)

    bind = op.get_bind()
    bind.execute(sa.text(f"DROP TABLE IF EXISTS {APP_SCHEMA}.revealed_preferences"))


def downgrade() -> None:
    """Recreate the dropped thread-scoped preference table."""

    op.drop_index("ix_project_facts_run_id", table_name="project_facts", schema=APP_SCHEMA)
    op.drop_index("ix_project_facts_project_id", table_name="project_facts", schema=APP_SCHEMA)
    op.drop_table("project_facts", schema=APP_SCHEMA)

    op.drop_index("ix_room_facts_run_id", table_name="room_facts", schema=APP_SCHEMA)
    op.drop_index("ix_room_facts_room_id", table_name="room_facts", schema=APP_SCHEMA)
    op.drop_table("room_facts", schema=APP_SCHEMA)

    op.create_table(
        "revealed_preferences",
        sa.Column("revealed_preference_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("signal_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.UniqueConstraint(
            "thread_id",
            "signal_key",
            "value",
            name="uq_revealed_preferences_thread_signal_value",
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_revealed_preferences_thread_id",
        "revealed_preferences",
        ["thread_id"],
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_revealed_preferences_run_id",
        "revealed_preferences",
        ["run_id"],
        schema=APP_SCHEMA,
    )
