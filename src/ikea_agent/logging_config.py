"""Logging configuration entrypoints.

The goal is to provide a consistent, context-rich logger configuration that can
be reused by ingestion and query pipelines once implementation begins.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(level_name: str, json_logs: bool) -> None:
    """Configure standard logging and structlog processors for local usage."""

    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO), format="%(message)s"
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
    ]

    renderer: structlog.types.Processor
    if json_logs:
        renderer = structlog.processors.JSONRenderer(sort_keys=True)
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level_name.upper(), logging.INFO),
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound logger with a component name pre-attached."""

    return structlog.get_logger().bind(component=name)
