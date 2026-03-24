"""Render one host deploy bundle from a validated release manifest.

The deploy bundle is the handoff artifact from CI to the EC2 host. It contains
only pinned image references, non-secret env files, the canonical manifest, the
compose file, and the host-side runner. The host is still responsible for
reading Secrets Manager and performing the deploy sequence.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from scripts.deploy.release_manifest import read_release_manifest, write_release_manifest

_DEFAULT_AWS_REGION = "eu-central-1"
_DEFAULT_COMPOSE_PROJECT_NAME = "ikea-agent-dev"
_DEFAULT_PRODUCT_IMAGE_BASE_URL = "https://designagent.talperry.com/static/product-images"
_DEFAULT_BACKEND_HOST_PORT = 8000
_DEFAULT_UI_HOST_PORT = 3000
_DEFAULT_DEPLOY_STATE_DIR = "/var/lib/ikea-agent/deploy"
_DEFAULT_HOST_ARTIFACT_ROOT_DIR = "/var/lib/ikea-agent/artifacts"
_DEFAULT_HOST_BOOTSTRAP_ROOT_DIR = "/var/lib/ikea-agent/bootstrap"
_CONTAINER_BOOTSTRAP_ROOT_DIR = "/var/lib/ikea-agent/bootstrap/ikea_image_catalog"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_file(*, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render one deploy bundle from a release manifest."
    )
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--backend-app-secret-arn", required=True)
    parser.add_argument("--model-provider-secret-arn", required=True)
    parser.add_argument("--observability-secret-arn", required=True)
    parser.add_argument("--database-secret-arn", required=True)
    parser.add_argument("--aws-region", default=_DEFAULT_AWS_REGION)
    parser.add_argument("--compose-project-name", default=_DEFAULT_COMPOSE_PROJECT_NAME)
    parser.add_argument("--product-image-base-url", default=_DEFAULT_PRODUCT_IMAGE_BASE_URL)
    parser.add_argument("--backend-host-port", type=int, default=_DEFAULT_BACKEND_HOST_PORT)
    parser.add_argument("--ui-host-port", type=int, default=_DEFAULT_UI_HOST_PORT)
    parser.add_argument("--deploy-state-dir", default=_DEFAULT_DEPLOY_STATE_DIR)
    parser.add_argument("--host-artifact-root-dir", default=_DEFAULT_HOST_ARTIFACT_ROOT_DIR)
    parser.add_argument("--host-bootstrap-root-dir", default=_DEFAULT_HOST_BOOTSTRAP_ROOT_DIR)
    return parser.parse_args()


def main() -> int:
    """Render one deploy bundle into the requested output directory."""

    args = _parse_args()
    manifest = read_release_manifest(args.release_manifest)

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    host_env = {
        "AWS_REGION": args.aws_region,
        "COMPOSE_PROJECT_NAME": args.compose_project_name,
        "PRODUCT_IMAGE_BASE_URL": args.product_image_base_url,
        "BACKEND_IMAGE_REF": manifest.backend_image.digest_ref,
        "UI_IMAGE_REF": manifest.ui_image.digest_ref,
        "BACKEND_APP_SECRET_ARN": args.backend_app_secret_arn,
        "MODEL_PROVIDER_SECRET_ARN": args.model_provider_secret_arn,
        "OBSERVABILITY_SECRET_ARN": args.observability_secret_arn,
        "DATABASE_SECRET_ARN": args.database_secret_arn,
        "BACKEND_HOST_PORT": str(args.backend_host_port),
        "UI_HOST_PORT": str(args.ui_host_port),
        "DEPLOY_STATE_DIR": args.deploy_state_dir,
        "HOST_ARTIFACT_ROOT_DIR": args.host_artifact_root_dir,
        "HOST_BOOTSTRAP_ROOT_DIR": args.host_bootstrap_root_dir,
        "RELEASE_VERSION": manifest.app_version,
        "RELEASE_GIT_TAG": manifest.git_tag,
        "RELEASE_GIT_SHA": manifest.git_sha,
    }
    backend_env = {
        "APP_ENV": "dev",
        "LOG_LEVEL": "INFO",
        "LOG_JSON": "true",
        "LOGFIRE_SERVICE_NAME": "ikea-agent",
        "LOGFIRE_ENVIRONMENT": "dev",
        "LOGFIRE_SERVICE_VERSION": manifest.app_version,
        "LOGFIRE_SEND_MODE": "if-token-present",
        "ALLOW_MODEL_REQUESTS": "1",
        "IMAGE_SERVING_STRATEGY": "direct_public_url",
        "IMAGE_SERVICE_BASE_URL": args.product_image_base_url,
        "ARTIFACT_ROOT_DIR": "/var/lib/ikea-agent/artifacts",
        "FEEDBACK_CAPTURE_ENABLED": "0",
        "TRACE_CAPTURE_ENABLED": "0",
        "IKEA_IMAGE_CATALOG_ROOT_DIR": _CONTAINER_BOOTSTRAP_ROOT_DIR,
        "IKEA_IMAGE_CATALOG_RUN_ID": "",
    }
    ui_env = {
        "NODE_ENV": "production",
        "PY_AG_UI_URL": "http://backend:8000/ag-ui/",
        "NEXT_PUBLIC_USE_MOCK_AGENT": "0",
        "NEXT_PUBLIC_TRACE_CAPTURE_ENABLED": "0",
    }

    _write_env_file(output_dir / "host.env", host_env)
    _write_env_file(output_dir / "backend.env", backend_env)
    _write_env_file(output_dir / "backend.secrets.env", {})
    _write_env_file(output_dir / "ui.env", ui_env)
    write_release_manifest(output_dir / "release-manifest.json", manifest)

    repo_root = _repo_root()
    _copy_file(
        source=repo_root / "docker" / "compose.deploy.yml",
        destination=output_dir / "docker-compose.yml",
    )
    _copy_file(
        source=repo_root / "scripts" / "deploy" / "host_bundle_runner.py",
        destination=output_dir / "scripts" / "host_bundle_runner.py",
    )

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
