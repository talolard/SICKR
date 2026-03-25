from __future__ import annotations

from scripts.deploy.apply_migrations import _alembic_config


def test_alembic_config_preserves_percent_encoded_database_urls() -> None:
    database_url = "postgresql+psycopg://ikea:p%40ssword@db.example.test:5432/ikea_agent"

    config = _alembic_config(database_url=database_url)

    assert config.get_main_option("sqlalchemy.url") == database_url
