"""Initialize Alembic migration foundation.

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "20260306_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    # Foundation migration intentionally starts as no-op.
    # Follow-up revisions introduce runtime persistence tables.
    return


def downgrade() -> None:
    """Revert schema changes."""

    return
