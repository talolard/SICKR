"""Execute one rendered deploy bundle on the EC2 host.

This runner intentionally uses only the Python standard library so the host can
execute it without a repo checkout or a prepared virtualenv. The deploy bundle
already contains the compose file, manifest, non-secret env files, and this
runner. The host still needs Docker, Docker Compose, AWS CLI, and access to the
runtime Secrets Manager values.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from urllib import request

_BACKEND_HEALTH_TIMEOUT_SECONDS = 180
_UI_HEALTH_TIMEOUT_SECONDS = 60
_HEALTH_POLL_INTERVAL_SECONDS = 5
_HTTP_SUCCESS_MIN = 200
_HTTP_SUCCESS_MAX_EXCLUSIVE = 300
_HOST_IMAGE_CATALOG_ROOT_SUFFIX = "ikea_image_catalog"
_CONTAINER_IMAGE_CATALOG_ROOT = Path("/var/lib/ikea-agent/bootstrap/ikea_image_catalog")


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


@contextmanager
def _deployment_lock(state_dir: Path) -> Generator[None]:
    """Serialize deploy and rollback actions on the host with one advisory lock."""

    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "deploy.lock"
    with lock_path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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


def _read_release_manifest_payload(bundle_dir: Path) -> dict[str, object]:
    payload = json.loads((bundle_dir / "release-manifest.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object release manifest in {bundle_dir / 'release-manifest.json'}."
        raise TypeError(msg)
    return payload


def _required_manifest_string(payload: dict[str, object], *path: str) -> str:
    value: object = payload
    for segment in path:
        if not isinstance(value, dict) or segment not in value:
            dotted = ".".join(path)
            msg = f"Missing required manifest field {dotted!r}."
            raise KeyError(msg)
        value = value[segment]
    if not isinstance(value, str) or not value:
        dotted = ".".join(path)
        msg = f"Expected non-empty string manifest field {dotted!r}."
        raise TypeError(msg)
    return value


def _catalog_source_for_run_dir(run_dir: Path) -> Path:
    parquet_path = run_dir / "catalog.parquet"
    if parquet_path.exists():
        return parquet_path
    jsonl_path = run_dir / "catalog.jsonl"
    if jsonl_path.exists():
        return jsonl_path
    msg = f"Configured image catalog run has no catalog file: {run_dir}"
    raise FileNotFoundError(msg)


def _fingerprint_virtual_file(*, virtual_path: Path, actual_path: Path) -> str:
    digest = sha256()
    resolved_actual_path = actual_path.expanduser().resolve()
    stat = resolved_actual_path.stat()
    digest.update(virtual_path.as_posix().encode())
    digest.update(str(stat.st_size).encode())
    digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def _expected_image_catalog_seed_version(
    *, host_env: dict[str, str], image_catalog_run_id: str
) -> str:
    host_bootstrap_root = Path(host_env["HOST_BOOTSTRAP_ROOT_DIR"])
    host_run_dir = (
        host_bootstrap_root / _HOST_IMAGE_CATALOG_ROOT_SUFFIX / "runs" / image_catalog_run_id
    )
    catalog_source = _catalog_source_for_run_dir(host_run_dir)
    container_source = (
        _CONTAINER_IMAGE_CATALOG_ROOT / "runs" / image_catalog_run_id / catalog_source.name
    )
    return _fingerprint_virtual_file(virtual_path=container_source, actual_path=catalog_source)


def _validate_bundle_contract(
    *, host_env: dict[str, str], manifest_payload: dict[str, object]
) -> dict[str, str]:
    release_tag = _required_manifest_string(manifest_payload, "git_tag")
    release_sha = _required_manifest_string(manifest_payload, "git_sha")
    if host_env["RELEASE_GIT_TAG"] != release_tag:
        msg = (
            "Host env release tag does not match the manifest. "
            f"{host_env['RELEASE_GIT_TAG']!r} != {release_tag!r}"
        )
        raise ValueError(msg)
    if host_env["RELEASE_GIT_SHA"] != release_sha:
        msg = (
            "Host env release SHA does not match the manifest. "
            f"{host_env['RELEASE_GIT_SHA']!r} != {release_sha!r}"
        )
        raise ValueError(msg)
    for env_key, manifest_path in (
        ("BACKEND_IMAGE_REF", ("backend_image", "digest_ref")),
        ("UI_IMAGE_REF", ("ui_image", "digest_ref")),
    ):
        manifest_value = _required_manifest_string(manifest_payload, *manifest_path)
        if host_env[env_key] != manifest_value:
            msg = (
                f"Host env {env_key} does not match the manifest. "
                f"{host_env[env_key]!r} != {manifest_value!r}"
            )
            raise ValueError(msg)
    return {
        "postgres_seed_version": _required_manifest_string(
            manifest_payload, "bootstrap", "postgres_seed_version"
        ),
        "image_catalog_run_id": _required_manifest_string(
            manifest_payload, "bootstrap", "image_catalog_run_id"
        ),
        "release_tag": release_tag,
    }


def _write_runtime_secret_env(*, host_env: dict[str, str], values: dict[str, str]) -> Path:
    runtime_secret_path = Path(host_env["BACKEND_SECRETS_ENV_FILE"])
    runtime_secret_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = runtime_secret_path.with_name(runtime_secret_path.name + ".tmp")
    _write_env_file(temporary_path, values)
    temporary_path.chmod(0o600)
    temporary_path.replace(runtime_secret_path)
    return runtime_secret_path


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
    manifest_payload = _read_release_manifest_payload(bundle_dir)
    bundle_contract = _validate_bundle_contract(
        host_env=host_env, manifest_payload=manifest_payload
    )
    expected_image_catalog_seed_version = _expected_image_catalog_seed_version(
        host_env=host_env,
        image_catalog_run_id=bundle_contract["image_catalog_run_id"],
    )
    _write_runtime_secret_env(host_env=host_env, values=_merged_backend_secrets(host_env))
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
                "--image-catalog-root",
                _CONTAINER_IMAGE_CATALOG_ROOT.as_posix(),
                "--image-catalog-run-id",
                bundle_contract["image_catalog_run_id"],
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
            "--expected-postgres-seed-version",
            bundle_contract["postgres_seed_version"],
            "--expected-image-catalog-seed-version",
            expected_image_catalog_seed_version,
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

    _record_release_state(
        bundle_dir=bundle_dir,
        state_dir=state_dir,
        release_tag=bundle_contract["release_tag"],
    )


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
        state_dir = args.state_dir.resolve()
        with _deployment_lock(state_dir):
            _deploy_bundle(
                bundle_dir=args.bundle_dir.resolve(),
                state_dir=state_dir,
                run_migrations=True,
                run_bootstrap=True,
            )
        return 0
    if args.command == "rollback-previous":
        state_dir = args.state_dir.resolve()
        with _deployment_lock(state_dir):
            _rollback_previous(state_dir=state_dir)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
