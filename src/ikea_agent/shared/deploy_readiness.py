"""Shared deploy-readiness checks used by health routes and deploy scripts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Table, func, select

from ikea_agent.retrieval.schema import product_embeddings, product_images, products_canonical
from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.ops_schema import seed_state

REQUIRED_SEED_SYSTEMS: tuple[str, ...] = (
    POSTGRES_SEED_SYSTEM,
    IMAGE_CATALOG_SEED_SYSTEM,
)

_REQUIRED_TABLE_NAMES: dict[str, Table] = {
    "catalog.products_canonical": products_canonical,
    "catalog.product_embeddings": product_embeddings,
    "catalog.product_images": product_images,
}


@dataclass(frozen=True, slots=True)
class DeployCheckResult:
    """Compact machine-readable outcome for one deploy-readiness check."""

    status: Literal["ok", "failed"]
    detail: str


@dataclass(frozen=True, slots=True)
class SeedVerificationDetails:
    """Observable seed-state and seeded-table facts needed for deploy decisions."""

    systems: dict[str, dict[str, str]]
    table_counts: dict[str, int]
    missing_public_image_urls: int | None


@dataclass(frozen=True, slots=True)
class SeedVerificationResult:
    """Full seed verification outcome for readiness and deploy scripts."""

    seed_state: DeployCheckResult
    catalog_data: DeployCheckResult
    details: SeedVerificationDetails


def collect_seed_verification(
    engine: Engine,
    *,
    image_serving_strategy: Literal["backend_proxy", "direct_public_url"],
) -> SeedVerificationResult:
    """Return the seed-state and seeded-table checks required for deploy readiness."""

    with engine.connect() as connection:
        seed_rows = connection.execute(
            select(seed_state.c.system_name, seed_state.c.status, seed_state.c.version).where(
                seed_state.c.system_name.in_(REQUIRED_SEED_SYSTEMS)
            )
        ).all()
        table_counts = {
            table_name: int(
                connection.execute(select(func.count()).select_from(table)).scalar_one()
            )
            for table_name, table in _REQUIRED_TABLE_NAMES.items()
        }
        missing_public_image_urls = (
            int(
                connection.execute(
                    select(func.count())
                    .select_from(product_images)
                    .where(
                        product_images.c.public_url.is_(None)
                        | (func.trim(product_images.c.public_url) == "")
                    )
                ).scalar_one()
            )
            if image_serving_strategy == "direct_public_url"
            else None
        )

    systems = {
        str(system_name): {
            "status": str(status),
            "version": str(version),
        }
        for system_name, status, version in seed_rows
    }
    seed_state_check = _build_seed_state_check(systems)
    catalog_data_check = _build_catalog_data_check(
        table_counts=table_counts,
        image_serving_strategy=image_serving_strategy,
        missing_public_image_urls=missing_public_image_urls,
    )
    return SeedVerificationResult(
        seed_state=seed_state_check,
        catalog_data=catalog_data_check,
        details=SeedVerificationDetails(
            systems=systems,
            table_counts=table_counts,
            missing_public_image_urls=missing_public_image_urls,
        ),
    )


def _build_seed_state_check(systems: dict[str, dict[str, str]]) -> DeployCheckResult:
    missing = [system_name for system_name in REQUIRED_SEED_SYSTEMS if system_name not in systems]
    unready = [
        system_name
        for system_name in REQUIRED_SEED_SYSTEMS
        if systems.get(system_name, {}).get("status") not in {None, "ready"}
    ]
    if missing:
        return DeployCheckResult(
            status="failed",
            detail=f"Missing seed state rows: {', '.join(sorted(missing))}.",
        )
    if unready:
        return DeployCheckResult(
            status="failed",
            detail=f"Seed state not ready: {', '.join(sorted(unready))}.",
        )
    return DeployCheckResult(
        status="ok",
        detail="Required seed state rows are ready.",
    )


def _build_catalog_data_check(
    *,
    table_counts: dict[str, int],
    image_serving_strategy: Literal["backend_proxy", "direct_public_url"],
    missing_public_image_urls: int | None,
) -> DeployCheckResult:
    empty_tables = [table_name for table_name, row_count in table_counts.items() if row_count <= 0]
    if empty_tables:
        return DeployCheckResult(
            status="failed",
            detail=f"Seeded catalog tables are empty: {', '.join(sorted(empty_tables))}.",
        )
    if image_serving_strategy == "direct_public_url" and missing_public_image_urls:
        return DeployCheckResult(
            status="failed",
            detail=(
                "Product image metadata is not ready for direct_public_url because "
                f"{missing_public_image_urls} image rows are missing public_url values."
            ),
        )
    return DeployCheckResult(
        status="ok",
        detail="Seeded catalog tables are populated for deploy traffic.",
    )
