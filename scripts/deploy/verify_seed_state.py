"""Verify that the required deployment seed-state rows are present and ready."""

from __future__ import annotations

import argparse
import json

from sqlalchemy import select

from ikea_agent.config import get_settings
from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.ops_schema import seed_state
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url


def main() -> None:
    """Check that required seed-state systems are present and marked ready."""

    parser = argparse.ArgumentParser(description="Verify deployment seed-state readiness.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    settings = get_settings()
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    engine = create_database_engine(database_url)
    required = (POSTGRES_SEED_SYSTEM, IMAGE_CATALOG_SEED_SYSTEM)

    with engine.connect() as connection:
        rows = connection.execute(
            select(seed_state.c.system_name, seed_state.c.status, seed_state.c.version).where(
                seed_state.c.system_name.in_(required)
            )
        ).all()

    by_name = {
        str(system_name): {"status": str(status), "version": str(version)}
        for system_name, status, version in rows
    }
    missing = [system_name for system_name in required if system_name not in by_name]
    unready = [
        system_name
        for system_name in required
        if by_name.get(system_name, {}).get("status") != "ready"
    ]
    payload = {
        "status": "ok" if not missing and not unready else "not_ready",
        "systems": by_name,
        "missing": missing,
        "unready": unready,
    }
    print(json.dumps(payload, sort_keys=True))
    if payload["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
