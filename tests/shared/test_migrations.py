from __future__ import annotations

from pathlib import Path

import duckdb
from alembic import command
from alembic.config import Config


def test_alembic_upgrade_creates_conversation_persistence_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_test.duckdb"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"duckdb:///{db_path}")
    cfg.set_main_option("script_location", "migrations")

    command.upgrade(cfg, "head")

    connection = duckdb.connect(str(db_path))
    rows = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'app'
        ORDER BY table_name
        """
    ).fetchall()
    table_names = {str(row[0]) for row in rows}

    assert {
        "threads",
        "agent_runs",
        "message_archives",
        "assets",
        "floor_plan_revisions",
        "analysis_runs",
        "analysis_input_assets",
        "analysis_detections",
        "search_runs",
        "search_results",
        "room_3d_assets",
        "room_3d_snapshots",
    }.issubset(table_names)
