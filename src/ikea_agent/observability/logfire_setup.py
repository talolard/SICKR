"""Logfire bootstrap helpers for backend runtime instrumentation."""

from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from threading import Lock
from typing import Literal

import logfire
from fastapi import FastAPI

from ikea_agent.config import AppSettings

logger = getLogger(__name__)

_CONFIG_LOCK = Lock()
_LOGFIRE_CONFIGURED = False
_PYDANTIC_AI_INSTRUMENTED = False


def configure_logfire(settings: AppSettings) -> None:
    """Configure Logfire globally once, warning (not failing) when token is missing."""

    global _LOGFIRE_CONFIGURED  # noqa: PLW0603
    global _PYDANTIC_AI_INSTRUMENTED  # noqa: PLW0603

    with _CONFIG_LOCK:
        if not _LOGFIRE_CONFIGURED:
            _warn_if_logfire_export_disabled(settings)
            send_mode: Literal["if-token-present"] | bool
            if settings.logfire_send_mode == "if-token-present":
                send_mode = "if-token-present"
            else:
                send_mode = True
            logfire.configure(
                token=settings.logfire_token,
                send_to_logfire=send_mode,
                service_name=settings.logfire_service_name,
                service_version=settings.logfire_service_version,
                environment=settings.logfire_environment or settings.app_env,
            )
            _LOGFIRE_CONFIGURED = True
        if not _PYDANTIC_AI_INSTRUMENTED:
            logfire.instrument_pydantic_ai()
            _PYDANTIC_AI_INSTRUMENTED = True


def instrument_fastapi_app(app: FastAPI) -> None:
    """Instrument one FastAPI app instance with Logfire tracing."""

    logfire.instrument_fastapi(app)


def _warn_if_logfire_export_disabled(settings: AppSettings) -> None:
    has_token = bool(
        settings.logfire_token
        or os.getenv("LOGFIRE_TOKEN")
        or os.getenv("APP_LOGFIRE_TOKEN")
        or _logfire_credentials_file().exists()
    )
    if has_token:
        return
    logger.warning(
        "logfire_export_disabled_no_token",
        extra={
            "logfire_send_mode": settings.logfire_send_mode,
            "hint": "Set LOGFIRE_TOKEN or APP_LOGFIRE_TOKEN to enable remote export.",
        },
    )


def _logfire_credentials_file() -> Path:
    return Path.cwd() / ".logfire" / "logfire_credentials.json"
