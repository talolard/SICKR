"""Health and readiness routes for deploy-safe runtime checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, inspect, select, text

from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.ops_schema import seed_state

_REQUIRED_SEED_SYSTEMS: tuple[str, ...] = (
    POSTGRES_SEED_SYSTEM,
    IMAGE_CATALOG_SEED_SYSTEM,
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


def _seed_state_check(engine: Engine) -> HealthCheckResult:
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                seed_state.c.system_name,
                seed_state.c.status,
            ).where(seed_state.c.system_name.in_(_REQUIRED_SEED_SYSTEMS))
        ).all()

    states = {str(system_name): str(status) for system_name, status in rows}
    missing = [system_name for system_name in _REQUIRED_SEED_SYSTEMS if system_name not in states]
    unready = [
        system_name
        for system_name in _REQUIRED_SEED_SYSTEMS
        if states.get(system_name) not in {None, "ready"}
    ]
    if missing:
        return HealthCheckResult(
            status="failed",
            detail=f"Missing seed state rows: {', '.join(sorted(missing))}.",
        )
    if unready:
        return HealthCheckResult(
            status="failed",
            detail=f"Seed state not ready: {', '.join(sorted(unready))}.",
        )
    return HealthCheckResult(
        status="ok",
        detail="Required seed state rows are ready.",
    )


def _readiness_payload(engine: Engine | None) -> tuple[int, dict[str, object]]:
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
        schema_check = _schema_check(engine)
        seed_check = _seed_state_check(engine)
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
            },
        }
        return 503, payload

    checks: dict[str, dict[str, str]] = {
        "database": asdict(database_check),
        "schema": asdict(schema_check),
        "seed_state": asdict(seed_check),
    }
    if all(check["status"] == "ok" for check in checks.values()):
        return 200, {"status": "ok", "checks": checks}
    return 503, {"status": "not_ready", "checks": checks}


def register_health_routes(app: FastAPI, *, engine: Engine | None) -> None:
    """Register liveness and readiness routes used by deploy automation."""

    @app.get("/api/health/live")
    async def live_health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health")
    @app.get("/api/health/ready")
    async def ready_health() -> JSONResponse:
        status_code, payload = _readiness_payload(engine)
        return JSONResponse(status_code=status_code, content=payload)
