"""Execute one rendered deploy bundle on the EC2 host.

This runner intentionally uses only the Python standard library so the host can
execute it without a repo checkout or a prepared virtualenv. The deploy bundle
already contains the compose file, manifest, non-secret env files, and this
runner. The host still needs Docker, Docker Compose, AWS CLI, and access to the
runtime Secrets Manager values.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib import request

_BACKEND_HEALTH_TIMEOUT_SECONDS = 180
_UI_HEALTH_TIMEOUT_SECONDS = 60
_HEALTH_POLL_INTERVAL_SECONDS = 5
_HTTP_SUCCESS_MIN = 200
_HTTP_SUCCESS_MAX_EXCLUSIVE = 300


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            msg = f"Expected KEY=VALUE line in {path}, found {raw_line!r}."
            raise ValueError(msg)
        values[key] = value
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> str:
    print("+", " ".join(args))
    completed = subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        command_text = " ".join(args)
        msg = f"Command failed with exit code {completed.returncode}: {command_text}"
        raise RuntimeError(msg)
    return completed.stdout


def _compose_command(bundle_dir: Path, host_env: dict[str, str], *args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        host_env["COMPOSE_PROJECT_NAME"],
        "--env-file",
        str(bundle_dir / "host.env"),
        "-f",
        str(bundle_dir / "docker-compose.yml"),
        *args,
    ]


def _secret_value(secret_arn: str, *, region: str) -> dict[str, str]:
    output = _run_command(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--region",
            region,
            "--secret-id",
            secret_arn,
            "--query",
            "SecretString",
            "--output",
            "text",
        ]
    ).strip()
    if output in {"", "None"}:
        return {}
    loaded = json.loads(output)
    if not isinstance(loaded, dict):
        loaded_type = type(loaded).__name__
        msg = f"Expected JSON object secret payload for {secret_arn}, found {loaded_type}."
        raise TypeError(msg)
    values: dict[str, str] = {}
    for key, value in loaded.items():
        values[str(key)] = "" if value is None else str(value)
    return values


def _merged_backend_secrets(host_env: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for secret_name in (
        "BACKEND_APP_SECRET_ARN",
        "MODEL_PROVIDER_SECRET_ARN",
        "OBSERVABILITY_SECRET_ARN",
        "DATABASE_SECRET_ARN",
    ):
        secret_values = _secret_value(host_env[secret_name], region=host_env["AWS_REGION"])
        for key, value in secret_values.items():
            existing = merged.get(key)
            if existing is not None and existing != value:
                msg = f"Conflicting secret values found for environment key {key!r}."
                raise ValueError(msg)
            merged[key] = value
    return merged


def _unique_registries(host_env: dict[str, str]) -> list[str]:
    registries = {
        host_env["BACKEND_IMAGE_REF"].split("/", 1)[0],
        host_env["UI_IMAGE_REF"].split("/", 1)[0],
    }
    return sorted(registries)


def _login_ecr(host_env: dict[str, str]) -> None:
    region = host_env["AWS_REGION"]
    for registry in _unique_registries(host_env):
        password = _run_command(["aws", "ecr", "get-login-password", "--region", region])
        _run_command(
            ["docker", "login", "--username", "AWS", "--password-stdin", registry],
            input_text=password,
        )


def _wait_for_http_success(url: str, *, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with request.urlopen(url, timeout=10) as response:  # noqa: S310
                if _HTTP_SUCCESS_MIN <= response.status < _HTTP_SUCCESS_MAX_EXCLUSIVE:
                    return
                last_error = RuntimeError(f"{url} returned status {response.status}")
        except Exception as exc:
            last_error = exc
        time.sleep(_HEALTH_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def _record_release_state(*, bundle_dir: Path, state_dir: Path, release_tag: str) -> None:
    current_tag_path = state_dir / "current_release_tag.txt"
    previous_tag_path = state_dir / "previous_release_tag.txt"
    current_manifest_path = state_dir / "current_release_manifest.json"
    previous_manifest_path = state_dir / "previous_release_manifest.json"

    current_tag: str | None = None
    if current_tag_path.exists():
        value = current_tag_path.read_text(encoding="utf-8").strip()
        current_tag = value or None

    if current_tag and current_tag != release_tag:
        previous_tag_path.write_text(current_tag + "\n", encoding="utf-8")
        if current_manifest_path.exists():
            previous_manifest_path.write_text(
                current_manifest_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    current_tag_path.write_text(release_tag + "\n", encoding="utf-8")
    current_manifest_path.write_text(
        (bundle_dir / "release-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def _deploy_bundle(
    *,
    bundle_dir: Path,
    state_dir: Path,
    run_migrations: bool,
    run_bootstrap: bool,
) -> None:
    host_env = _read_env_file(bundle_dir / "host.env")
    release_tag = host_env["RELEASE_GIT_TAG"]
    backend_secrets_path = bundle_dir / "backend.secrets.env"
    _write_env_file(backend_secrets_path, _merged_backend_secrets(host_env))
    _login_ecr(host_env)

    _run_command(_compose_command(bundle_dir, host_env, "pull", "backend", "ui"))
    if run_migrations:
        _run_command(
            _compose_command(
                bundle_dir,
                host_env,
                "run",
                "--rm",
                "backend",
                "python",
                "-m",
                "scripts.deploy.apply_migrations",
            )
        )
    if run_bootstrap:
        _run_command(
            _compose_command(
                bundle_dir,
                host_env,
                "run",
                "--rm",
                "backend",
                "python",
                "-m",
                "scripts.deploy.bootstrap_catalog",
            )
        )
    _run_command(
        _compose_command(
            bundle_dir,
            host_env,
            "run",
            "--rm",
            "backend",
            "python",
            "-m",
            "scripts.deploy.verify_seed_state",
        )
    )

    _run_command(_compose_command(bundle_dir, host_env, "up", "-d", "backend"))
    backend_port = host_env["BACKEND_HOST_PORT"]
    _wait_for_http_success(
        f"http://127.0.0.1:{backend_port}/api/health/live",
        timeout_seconds=_BACKEND_HEALTH_TIMEOUT_SECONDS,
    )
    _wait_for_http_success(
        f"http://127.0.0.1:{backend_port}/api/health/ready",
        timeout_seconds=_BACKEND_HEALTH_TIMEOUT_SECONDS,
    )

    _run_command(_compose_command(bundle_dir, host_env, "up", "-d", "ui"))
    ui_port = host_env["UI_HOST_PORT"]
    _wait_for_http_success(
        f"http://127.0.0.1:{ui_port}/api/health",
        timeout_seconds=_UI_HEALTH_TIMEOUT_SECONDS,
    )
    _wait_for_http_success(
        f"http://127.0.0.1:{ui_port}/api/agents",
        timeout_seconds=_UI_HEALTH_TIMEOUT_SECONDS,
    )
    _wait_for_http_success(
        f"http://127.0.0.1:{ui_port}/agents/search",
        timeout_seconds=_UI_HEALTH_TIMEOUT_SECONDS,
    )

    _record_release_state(bundle_dir=bundle_dir, state_dir=state_dir, release_tag=release_tag)


def _rollback_previous(*, state_dir: Path) -> None:
    previous_tag_path = state_dir / "previous_release_tag.txt"
    if not previous_tag_path.exists():
        msg = f"No previous release tag recorded under {state_dir}."
        raise FileNotFoundError(msg)
    previous_tag = previous_tag_path.read_text(encoding="utf-8").strip()
    if not previous_tag:
        msg = f"Previous release tag file is empty under {state_dir}."
        raise ValueError(msg)
    bundle_dir = state_dir / "releases" / previous_tag
    if not bundle_dir.exists():
        msg = f"Previous release bundle does not exist: {bundle_dir}"
        raise FileNotFoundError(msg)
    _deploy_bundle(
        bundle_dir=bundle_dir,
        state_dir=state_dir,
        run_migrations=False,
        run_bootstrap=False,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one deploy bundle on the host.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy")
    deploy_parser.add_argument("--bundle-dir", type=Path, required=True)
    deploy_parser.add_argument("--state-dir", type=Path, required=True)

    rollback_parser = subparsers.add_parser("rollback-previous")
    rollback_parser.add_argument("--state-dir", type=Path, required=True)

    return parser.parse_args()


def main() -> int:
    """Execute one deploy or rollback operation."""

    args = _parse_args()
    if args.command == "deploy":
        _deploy_bundle(
            bundle_dir=args.bundle_dir.resolve(),
            state_dir=args.state_dir.resolve(),
            run_migrations=True,
            run_bootstrap=True,
        )
        return 0
    if args.command == "rollback-previous":
        _rollback_previous(state_dir=args.state_dir.resolve())
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
