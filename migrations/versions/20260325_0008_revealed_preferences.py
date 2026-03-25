"""Add durable revealed preference storage to the runtime schema.

Revision ID: 20260325_0008
Revises: 20260320_0013
Create Date: 2026-03-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

APP_SCHEMA = "app"
TABLE_NAME = "revealed_preferences"

# revision identifiers, used by Alembic.
revision: str = "20260325_0008"
down_revision: str | Sequence[str] | None = "20260320_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the revealed preference table for Postgres environments."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names(schema=APP_SCHEMA))
    if TABLE_NAME in existing_tables:
        existing_indexes = {
            index["name"] for index in inspector.get_indexes(TABLE_NAME, schema=APP_SCHEMA)
        }
        if "ix_revealed_preferences_thread_id" not in existing_indexes:
            op.create_index(
                "ix_revealed_preferences_thread_id",
                TABLE_NAME,
                ["thread_id"],
                unique=False,
                schema=APP_SCHEMA,
            )
        if "ix_revealed_preferences_run_id" not in existing_indexes:
            op.create_index(
                "ix_revealed_preferences_run_id",
                TABLE_NAME,
                ["run_id"],
                unique=False,
                schema=APP_SCHEMA,
            )
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("revealed_preference_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("signal_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            [f"{APP_SCHEMA}.agent_runs.run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            [f"{APP_SCHEMA}.threads.thread_id"],
        ),
        sa.PrimaryKeyConstraint("revealed_preference_id"),
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
        TABLE_NAME,
        ["thread_id"],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_revealed_preferences_run_id",
        TABLE_NAME,
        ["run_id"],
        unique=False,
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Remove the revealed preference table."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    if TABLE_NAME not in set(inspector.get_table_names(schema=APP_SCHEMA)):
        return

    op.drop_index("ix_revealed_preferences_run_id", table_name=TABLE_NAME, schema=APP_SCHEMA)
    op.drop_index("ix_revealed_preferences_thread_id", table_name=TABLE_NAME, schema=APP_SCHEMA)
    op.drop_table(TABLE_NAME, schema=APP_SCHEMA)
