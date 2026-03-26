"""Run the canonical ECS release deploy flow from immutable image references.

This module keeps the deploy order in Python so the shared ECS orchestration is
tested in-repo instead of duplicated inline in GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from scripts.deploy.check_public_deploy_endpoints import check_public_deploy_endpoints
from scripts.deploy.render_ecs_task_definition import render_task_definition
from scripts.deploy.wait_for_ecs_service_rollout import wait_for_service_rollout


class CommandRunner(Protocol):
    """Run one command and return its stdout."""

    def __call__(self, argv: list[str]) -> str:
        """Return stdout for one already-tokenized command."""


def _default_command_runner(argv: list[str]) -> str:
    executable = shutil.which(argv[0])
    if executable is None:
        msg = f"{argv[0]} CLI not found in PATH."
        raise RuntimeError(msg)
    return subprocess.check_output([executable, *argv[1:]], text=True)  # noqa: S603


@dataclass(frozen=True, slots=True)
class ReleaseDeployRequest:
    """Inputs needed to roll one immutable release through ECS."""

    cluster_name: str
    backend_service_name: str
    ui_service_name: str
    backend_task_definition_family: str
    ui_task_definition_family: str
    backend_run_task_subnet_ids: tuple[str, ...]
    backend_run_task_security_group_ids: tuple[str, ...]
    app_alb_dns_name: str
    app_version: str
    backend_image_ref: str
    ui_image_ref: str
    postgres_seed_version: str
    public_app_base_url: str
    backend_desired_count: int = 1
    ui_desired_count: int = 1
    backend_rollout_timeout_seconds: float = 900.0
    backend_rollout_poll_seconds: float = 15.0


@dataclass(frozen=True, slots=True)
class ReleaseDeployResult:
    """High-level summary for one completed ECS release deploy."""

    alb_dns_name: str
    backend_task_definition_arn: str
    ui_task_definition_arn: str
    backend_service_name: str
    ui_service_name: str
    public_app_base_url: str


@dataclass(frozen=True, slots=True)
class AwsCli:
    """Minimal AWS CLI adapter so orchestration logic stays easy to test."""

    run_command: CommandRunner = _default_command_runner

    def json(self, *args: str) -> object:
        """Return parsed JSON output for one AWS CLI command."""

        raw = self.run_command(["aws", *args]).strip()
        if not raw:
            return {}
        return json.loads(raw)

    def text(self, *args: str) -> str:
        """Return stripped text output for one AWS CLI command."""

        return self.run_command(["aws", *args]).strip()

    def call(self, *args: str) -> None:
        """Run one AWS CLI command when the exit code is the only signal."""

        self.run_command(["aws", *args])


def describe_service(*, cluster: str, service_name: str, aws_cli: AwsCli) -> dict[str, Any]:
    """Return one ECS service payload."""

    payload = _require_dict(
        aws_cli.json(
            "ecs",
            "describe-services",
            "--cluster",
            cluster,
            "--services",
            service_name,
        ),
        "ECS service description",
    )
    services = payload.get("services", [])
    if not services:
        msg = f"ECS service not found: {service_name}"
        raise RuntimeError(msg)
    service = services[0]
    if not isinstance(service, dict):
        msg = f"Unexpected ECS service payload for {service_name!r}."
        raise TypeError(msg)
    return service


def describe_task_definition(*, task_definition_arn: str, aws_cli: AwsCli) -> dict[str, Any]:
    """Return one ECS task definition payload for a family or full ARN."""

    return _require_dict(
        aws_cli.json(
            "ecs",
            "describe-task-definition",
            "--task-definition",
            task_definition_arn,
            "--query",
            "taskDefinition",
        ),
        f"task definition {task_definition_arn}",
    )


def build_backend_network_configuration(
    *,
    subnet_ids: tuple[str, ...],
    security_group_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Return one awsvpc config from the Terraform-owned deploy contract."""

    if not subnet_ids:
        msg = "Expected at least one backend run-task subnet id."
        raise ValueError(msg)
    if not security_group_ids:
        msg = "Expected at least one backend run-task security group id."
        raise ValueError(msg)
    return {
        "awsvpcConfiguration": {
            "subnets": list(subnet_ids),
            "securityGroups": list(security_group_ids),
            "assignPublicIp": "ENABLED",
        }
    }


def register_task_definition(*, task_definition: dict[str, Any], aws_cli: AwsCli) -> str:
    """Register one rendered ECS task definition and return its ARN."""

    return aws_cli.text(
        "ecs",
        "register-task-definition",
        "--cli-input-json",
        json.dumps(task_definition, separators=(",", ":")),
        "--query",
        "taskDefinition.taskDefinitionArn",
        "--output",
        "text",
    )


def run_one_off_backend_task_to_completion(
    *,
    cluster: str,
    task_definition_arn: str,
    network_configuration: dict[str, Any],
    command: list[str],
    aws_cli: AwsCli,
) -> str:
    """Run one backend one-off task and fail if the container exits non-zero."""

    payload = _require_dict(
        aws_cli.json(
            "ecs",
            "run-task",
            "--cluster",
            cluster,
            "--launch-type",
            "FARGATE",
            "--task-definition",
            task_definition_arn,
            "--network-configuration",
            json.dumps(network_configuration, separators=(",", ":")),
            "--overrides",
            json.dumps(_container_override(command), separators=(",", ":")),
        ),
        "ECS run-task response",
    )
    task_arn = _extract_task_arn(payload)
    aws_cli.call("ecs", "wait", "tasks-stopped", "--cluster", cluster, "--tasks", task_arn)
    describe_payload = _require_dict(
        aws_cli.json("ecs", "describe-tasks", "--cluster", cluster, "--tasks", task_arn),
        "ECS describe-tasks response",
    )
    exit_code = resolve_backend_exit_code(describe_payload)
    if exit_code != 0:
        msg = f"Backend task {task_arn} failed with exit code {exit_code}."
        raise RuntimeError(f"{msg} Payload: {json.dumps(describe_payload, sort_keys=True)}")
    return task_arn


def resolve_backend_exit_code(payload: dict[str, Any]) -> int | None:
    """Return the backend container exit code when the stopped task reports one."""

    tasks = payload.get("tasks", [])
    if not tasks:
        return None
    first_task = tasks[0]
    if not isinstance(first_task, dict):
        return None
    containers = first_task.get("containers", [])
    if not isinstance(containers, list):
        return None
    for container in containers:
        if not isinstance(container, dict):
            continue
        if container.get("name") != "backend":
            continue
        exit_code = container.get("exitCode")
        if exit_code is None:
            return None
        return int(exit_code)
    return None


def update_service(
    *,
    cluster: str,
    service_name: str,
    task_definition_arn: str,
    desired_count: int,
    aws_cli: AwsCli,
) -> None:
    """Update one ECS service to the expected task definition."""

    aws_cli.call(
        "ecs",
        "update-service",
        "--cluster",
        cluster,
        "--service",
        service_name,
        "--task-definition",
        task_definition_arn,
        "--desired-count",
        str(desired_count),
        "--force-new-deployment",
    )


def wait_for_backend_service_rollout(
    *,
    cluster: str,
    service_name: str,
    task_definition_arn: str,
    timeout_seconds: float,
    poll_seconds: float,
    aws_cli: AwsCli,
    sleep: Callable[[float], None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> None:
    """Wait until the backend service fully serves the new task definition."""

    sleep_fn = time.sleep if sleep is None else sleep
    result = wait_for_service_rollout(
        lambda: describe_service(cluster=cluster, service_name=service_name, aws_cli=aws_cli),
        expected_task_definition=task_definition_arn,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
        sleep=sleep_fn,
        monotonic=monotonic,
    )
    if result.status != "ok":
        msg = "Backend rollout did not complete: " + json.dumps(
            asdict(result.last_probe),
            sort_keys=True,
        )
        raise RuntimeError(msg)


def wait_for_ui_service_stable(*, cluster: str, service_name: str, aws_cli: AwsCli) -> None:
    """Wait until the UI service returns to a stable ECS state."""

    aws_cli.call(
        "ecs",
        "wait",
        "services-stable",
        "--cluster",
        cluster,
        "--services",
        service_name,
    )


def deploy_release(
    request: ReleaseDeployRequest,
    *,
    aws_cli: AwsCli | None = None,
    smoke_checker: Callable[[str], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> ReleaseDeployResult:
    """Roll one immutable release manifest through the shared ECS deploy path."""

    aws = aws_cli or AwsCli()
    smoke_check = check_public_deploy_endpoints if smoke_checker is None else smoke_checker
    backend_network_configuration = build_backend_network_configuration(
        subnet_ids=request.backend_run_task_subnet_ids,
        security_group_ids=request.backend_run_task_security_group_ids,
    )

    backend_task_definition = render_task_definition(
        payload=describe_task_definition(
            task_definition_arn=request.backend_task_definition_family,
            aws_cli=aws,
        ),
        container_name="backend",
        image=request.backend_image_ref,
        env_updates={"LOGFIRE_SERVICE_VERSION": request.app_version},
    )
    backend_task_definition_arn = register_task_definition(
        task_definition=backend_task_definition,
        aws_cli=aws,
    )

    run_one_off_backend_task_to_completion(
        cluster=request.cluster_name,
        task_definition_arn=backend_task_definition_arn,
        network_configuration=backend_network_configuration,
        command=["python", "-m", "scripts.deploy.apply_migrations"],
        aws_cli=aws,
    )
    run_one_off_backend_task_to_completion(
        cluster=request.cluster_name,
        task_definition_arn=backend_task_definition_arn,
        network_configuration=backend_network_configuration,
        command=[
            "python",
            "-m",
            "scripts.deploy.verify_seed_state",
            "--expected-postgres-seed-version",
            request.postgres_seed_version,
        ],
        aws_cli=aws,
    )

    update_service(
        cluster=request.cluster_name,
        service_name=request.backend_service_name,
        task_definition_arn=backend_task_definition_arn,
        desired_count=request.backend_desired_count,
        aws_cli=aws,
    )
    wait_for_backend_service_rollout(
        cluster=request.cluster_name,
        service_name=request.backend_service_name,
        task_definition_arn=backend_task_definition_arn,
        timeout_seconds=request.backend_rollout_timeout_seconds,
        poll_seconds=request.backend_rollout_poll_seconds,
        aws_cli=aws,
        sleep=sleep,
        monotonic=monotonic,
    )

    ui_task_definition = render_task_definition(
        payload=describe_task_definition(
            task_definition_arn=request.ui_task_definition_family,
            aws_cli=aws,
        ),
        container_name="ui",
        image=request.ui_image_ref,
        env_updates={
            "APP_RELEASE_VERSION": request.app_version,
            "PY_AG_UI_URL": f"http://{request.app_alb_dns_name}/ag-ui/",
            "BACKEND_PROXY_BASE_URL": f"http://{request.app_alb_dns_name}/",
        },
    )
    ui_task_definition_arn = register_task_definition(
        task_definition=ui_task_definition,
        aws_cli=aws,
    )
    update_service(
        cluster=request.cluster_name,
        service_name=request.ui_service_name,
        task_definition_arn=ui_task_definition_arn,
        desired_count=request.ui_desired_count,
        aws_cli=aws,
    )
    wait_for_ui_service_stable(
        cluster=request.cluster_name,
        service_name=request.ui_service_name,
        aws_cli=aws,
    )
    smoke_check(request.public_app_base_url)
    return ReleaseDeployResult(
        alb_dns_name=request.app_alb_dns_name,
        backend_task_definition_arn=backend_task_definition_arn,
        ui_task_definition_arn=ui_task_definition_arn,
        backend_service_name=request.backend_service_name,
        ui_service_name=request.ui_service_name,
        public_app_base_url=request.public_app_base_url,
    )


def _container_override(command: list[str]) -> dict[str, Any]:
    return {"containerOverrides": [{"name": "backend", "command": command}]}


def _extract_task_arn(payload: dict[str, Any]) -> str:
    tasks = payload.get("tasks", [])
    if isinstance(tasks, list) and tasks:
        first_task = tasks[0]
        if isinstance(first_task, dict):
            task_arn = first_task.get("taskArn")
            if isinstance(task_arn, str) and task_arn:
                return task_arn
    failures = payload.get("failures", [])
    msg = "Failed to start ECS one-off task. Payload: " + json.dumps(
        {"tasks": tasks, "failures": failures},
        sort_keys=True,
    )
    raise RuntimeError(msg)


def _require_str(value: object, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    msg = f"Expected non-empty string for {field_name}."
    raise TypeError(msg)


def _require_dict(value: object, context: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    msg = f"Expected JSON object for {context}."
    raise TypeError(msg)


def _parse_args() -> ReleaseDeployRequest:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--backend-service", required=True)
    parser.add_argument("--ui-service", required=True)
    parser.add_argument("--backend-task-definition-family", required=True)
    parser.add_argument("--ui-task-definition-family", required=True)
    parser.add_argument("--backend-run-task-subnets-json", required=True)
    parser.add_argument("--backend-run-task-security-groups-json", required=True)
    parser.add_argument("--app-alb-dns-name", required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--ui-image", required=True)
    parser.add_argument("--postgres-seed-version", required=True)
    parser.add_argument("--public-app-base-url", required=True)
    parser.add_argument("--backend-desired-count", type=int, default=1)
    parser.add_argument("--ui-desired-count", type=int, default=1)
    parser.add_argument("--backend-rollout-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--backend-rollout-poll-seconds", type=float, default=15.0)
    args = parser.parse_args()
    return ReleaseDeployRequest(
        cluster_name=args.cluster,
        backend_service_name=args.backend_service,
        ui_service_name=args.ui_service,
        backend_task_definition_family=args.backend_task_definition_family,
        ui_task_definition_family=args.ui_task_definition_family,
        backend_run_task_subnet_ids=_parse_string_list_argument(
            raw=args.backend_run_task_subnets_json,
            field_name="backend_run_task_subnet_ids",
        ),
        backend_run_task_security_group_ids=_parse_string_list_argument(
            raw=args.backend_run_task_security_groups_json,
            field_name="backend_run_task_security_group_ids",
        ),
        app_alb_dns_name=args.app_alb_dns_name,
        app_version=args.app_version,
        backend_image_ref=args.backend_image,
        ui_image_ref=args.ui_image,
        postgres_seed_version=args.postgres_seed_version,
        public_app_base_url=args.public_app_base_url,
        backend_desired_count=args.backend_desired_count,
        ui_desired_count=args.ui_desired_count,
        backend_rollout_timeout_seconds=args.backend_rollout_timeout_seconds,
        backend_rollout_poll_seconds=args.backend_rollout_poll_seconds,
    )


def _parse_string_list_argument(*, raw: str, field_name: str) -> tuple[str, ...]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Expected {field_name} to be valid JSON."
        raise ValueError(msg) from exc
    if not isinstance(payload, list) or not payload:
        msg = f"Expected {field_name} to be a non-empty JSON list of strings."
        raise ValueError(msg)
    values: list[str] = []
    for index, value in enumerate(payload):
        if not isinstance(value, str) or not value:
            msg = f"Expected {field_name}[{index}] to be a non-empty string."
            raise ValueError(msg)
        values.append(value)
    return tuple(values)


def main() -> int:
    """Execute one shared ECS release deploy and print a JSON summary."""

    result = deploy_release(_parse_args())
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
