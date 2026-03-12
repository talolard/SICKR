"""Add normalized analysis input-asset links.

Revision ID: 20260312_0004
Revises: 20260306_0003
Create Date: 2026-03-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260312_0004"
down_revision: str | Sequence[str] | None = "20260306_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.create_table(
        "analysis_input_assets",
        sa.Column("analysis_input_asset_id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], [f"{APP_SCHEMA}.analysis_runs.analysis_id"]),
        sa.ForeignKeyConstraint(["asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        sa.UniqueConstraint(
            "analysis_id",
            "ordinal",
            name="uq_analysis_input_assets_analysis_id_ordinal",
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_analysis_input_assets_analysis_id",
        "analysis_input_assets",
        ["analysis_id"],
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_analysis_input_assets_asset_id",
        "analysis_input_assets",
        ["asset_id"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_index(
        "ix_analysis_input_assets_asset_id",
        table_name="analysis_input_assets",
        schema=APP_SCHEMA,
    )
    op.drop_index(
        "ix_analysis_input_assets_analysis_id",
        table_name="analysis_input_assets",
        schema=APP_SCHEMA,
    )
    op.drop_table("analysis_input_assets", schema=APP_SCHEMA)
