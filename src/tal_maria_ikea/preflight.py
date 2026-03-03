"""Preflight checks for local setup.

Checks remain lightweight and avoid external API calls so they are safe to run
before credentials are fully provisioned.
"""

from __future__ import annotations

from pathlib import Path

from tal_maria_ikea.config import get_settings


class PreflightError(RuntimeError):
    """Raised when required local prerequisites are missing."""


def run_preflight() -> None:
    """Validate local configuration and expected files before development tasks."""

    settings = get_settings()

    if not settings.gcp_project_id:
        raise PreflightError("GCP_PROJECT_ID must be set.")

    if not settings.gcp_region:
        raise PreflightError("GCP_REGION must be set.")

    raw_csv_path = Path(settings.ikea_raw_csv_path)
    if not raw_csv_path.exists():
        raise PreflightError(f"Expected raw dataset at {raw_csv_path}.")


if __name__ == "__main__":
    run_preflight()
