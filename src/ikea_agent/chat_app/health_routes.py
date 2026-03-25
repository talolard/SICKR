"""Health and readiness routes for deploy-safe runtime checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, inspect, text

from ikea_agent.config import AppSettings
from ikea_agent.shared.deploy_readiness import (
    REQUIRED_SEED_SYSTEMS,
    DeployCheckResult,
    SeedVerificationDetails,
    SeedVerificationResult,
    collect_seed_verification,
)


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """One named health check with a compact machine-readable outcome."""

    status: Literal["ok", "failed", "skipped"]
    detail: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _alembic_config() -> Config:
    return Config(str(_repo_root() / "alembic.ini"))


def _sqlite_schema_is_bootstrapped(engine: Engine) -> bool:
    inspector = inspect(engine)
    return inspector.has_table("threads", schema="app") and inspector.has_table(
        "seed_state", schema="ops"
    )


def _schema_check(engine: Engine) -> HealthCheckResult:
    if engine.dialect.name == "sqlite":
        if _sqlite_schema_is_bootstrapped(engine):
            return HealthCheckResult(
                status="ok",
                detail="SQLite local runtime tables are present.",
            )
        return HealthCheckResult(
            status="failed",
            detail="SQLite local runtime tables are missing.",
        )

    head_revision = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
    if current_revision == head_revision:
        return HealthCheckResult(
            status="ok",
            detail=f"Alembic revision is at head ({head_revision}).",
        )
    return HealthCheckResult(
        status="failed",
        detail=f"Alembic revision {current_revision!r} does not match head {head_revision!r}.",
    )


def _coerce_health_check(result: DeployCheckResult) -> HealthCheckResult:
    return HealthCheckResult(status=result.status, detail=result.detail)


def _seed_verification_check(
    engine: Engine,
    *,
    settings: AppSettings,
) -> SeedVerificationResult:
    return collect_seed_verification(
        engine,
        image_serving_strategy=settings.image_serving_strategy,
    )


def _safe_dependency_check(
    *,
    label: str,
    check: Callable[[], HealthCheckResult],
) -> HealthCheckResult:
    try:
        return check()
    except Exception as exc:
        return HealthCheckResult(
            status="failed",
            detail=f"{label} check failed: {exc}",
        )


def _safe_seed_verification(
    engine: Engine,
    *,
    settings: AppSettings,
) -> SeedVerificationResult:
    try:
        return _seed_verification_check(engine, settings=settings)
    except Exception as exc:
        failed = DeployCheckResult(
            status="failed",
            detail=f"Seed verification failed: {exc}",
        )
        return SeedVerificationResult(
            seed_state=failed,
            catalog_data=failed,
            details=SeedVerificationDetails(
                systems={},
                table_counts={},
                missing_public_image_urls=None,
            ),
        )


def _readiness_payload(
    engine: Engine | None,
    *,
    settings: AppSettings,
) -> tuple[int, dict[str, object]]:
    if engine is None:
        payload: dict[str, object] = {
            "status": "not_ready",
            "checks": {
                "database": asdict(
                    HealthCheckResult(
                        status="failed",
                        detail="Runtime does not expose a SQLAlchemy engine.",
                    )
                ),
                "schema": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail="Schema check skipped because no database engine is available.",
                    )
                ),
                "seed_state": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail="Seed-state check skipped because no database engine is available.",
                    )
                ),
                "catalog_data": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail=(
                            "Catalog-data check skipped because no database engine is available."
                        ),
                    )
                ),
            },
        }
        return 503, payload

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_check = HealthCheckResult(
            status="ok",
            detail="Database connectivity is healthy.",
        )
    except Exception as exc:  # pragma: no cover - defensive health fallback
        payload = {
            "status": "not_ready",
            "checks": {
                "database": asdict(
                    HealthCheckResult(
                        status="failed",
                        detail=f"Readiness check failed: {exc}",
                    )
                ),
                "schema": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail="Schema check skipped because database connectivity failed.",
                    )
                ),
                "seed_state": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail="Seed-state check skipped because database connectivity failed.",
                    )
                ),
                "catalog_data": asdict(
                    HealthCheckResult(
                        status="skipped",
                        detail="Catalog-data check skipped because database connectivity failed.",
                    )
                ),
            },
        }
        return 503, payload

    seed_verification = _safe_seed_verification(engine, settings=settings)
    checks: dict[str, dict[str, str]] = {
        "database": asdict(database_check),
        "schema": asdict(
            _safe_dependency_check(label="schema", check=lambda: _schema_check(engine))
        ),
        "seed_state": asdict(_coerce_health_check(seed_verification.seed_state)),
        "catalog_data": asdict(_coerce_health_check(seed_verification.catalog_data)),
    }
    payload = {
        "status": "ok"
        if all(check["status"] == "ok" for check in checks.values())
        else "not_ready",
        "checks": checks,
        "details": {
            "required_seed_systems": list(REQUIRED_SEED_SYSTEMS),
            "seed_state": seed_verification.details.systems,
            "table_counts": seed_verification.details.table_counts,
            "missing_public_image_urls": seed_verification.details.missing_public_image_urls,
            "image_serving_strategy": settings.image_serving_strategy,
        },
    }
    return (200 if payload["status"] == "ok" else 503), payload


def register_health_routes(app: FastAPI, *, engine: Engine | None, settings: AppSettings) -> None:
    """Register liveness and readiness routes used by deploy automation."""

    @app.get("/api/health/live")
    async def live_health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health")
    @app.get("/api/health/ready")
    async def ready_health() -> JSONResponse:
        status_code, payload = _readiness_payload(engine, settings=settings)
        return JSONResponse(status_code=status_code, content=payload)
