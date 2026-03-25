"""Verify that the required deployment seed-state rows are present and ready."""

from __future__ import annotations

import argparse
import json

from ikea_agent.config import get_settings
from ikea_agent.shared.deploy_readiness import REQUIRED_SEED_SYSTEMS, collect_seed_verification
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url


def main() -> None:
    """Check that deploy-ready seed state and seeded catalog data are usable."""

    parser = argparse.ArgumentParser(description="Verify deployment seed-state readiness.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    settings = get_settings()
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
    engine = create_database_engine(database_url)
    verification = collect_seed_verification(
        engine,
        image_serving_strategy=settings.image_serving_strategy,
    )
    payload = {
        "status": (
            "ok"
            if verification.seed_state.status == "ok" and verification.catalog_data.status == "ok"
            else "not_ready"
        ),
        "required_seed_systems": list(REQUIRED_SEED_SYSTEMS),
        "image_serving_strategy": settings.image_serving_strategy,
        "checks": {
            "seed_state": {
                "status": verification.seed_state.status,
                "detail": verification.seed_state.detail,
            },
            "catalog_data": {
                "status": verification.catalog_data.status,
                "detail": verification.catalog_data.detail,
            },
        },
        "systems": verification.details.systems,
        "table_counts": verification.details.table_counts,
        "missing_public_image_urls": verification.details.missing_public_image_urls,
    }
    print(json.dumps(payload, sort_keys=True))
    if payload["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
