"""Shared Alembic config helpers for deployment scripts.

Alembic uses ConfigParser interpolation under the hood, so percent-encoded
credentials in database URLs must be escaped before calling
`Config.set_main_option`. The live deploy hit this exact footgun.
"""

from __future__ import annotations

from alembic.config import Config


def set_sqlalchemy_url(config: Config, database_url: str) -> None:
    """Set `sqlalchemy.url` on one Alembic config without losing `%` characters."""

    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
