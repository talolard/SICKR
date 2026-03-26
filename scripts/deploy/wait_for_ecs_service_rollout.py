"""Wait for one ECS service to finish rolling out one expected task definition."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ServiceRolloutProbeResult:
    """One ECS service rollout probe outcome."""

    ready: bool
    detail: str
    service_desired: int
    service_running: int
    service_task_definition: str | None
    primary_task_definition: str | None
    primary_desired: int | None
    primary_running: int | None
    primary_pending: int | None
    blocking_deployments: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ServiceRolloutWaitResult:
    """Aggregate status for a sequence of ECS rollout probes."""

    status: str
    attempts: int
    last_probe: ServiceRolloutProbeResult


def describe_service(*, cluster: str, service_name: str) -> dict[str, object]:
    """Return one ECS service description from the AWS CLI."""

    aws = shutil.which("aws")
    if aws is None:
        msg = "aws CLI not found in PATH."
        raise RuntimeError(msg)
    payload = json.loads(
        subprocess.check_output(  # noqa: S603
            [
                aws,
                "ecs",
                "describe-services",
                "--cluster",
                cluster,
                "--services",
                service_name,
            ],
            text=True,
        )
    )
    services = payload.get("services", [])
    if not services:
        msg = f"ECS service not found: {service_name}"
        raise RuntimeError(msg)
    return dict(services[0])


def probe_service_rollout(
    service: dict[str, object],
    *,
    expected_task_definition: str,
) -> ServiceRolloutProbeResult:
    """Check whether one ECS service is fully serving the expected revision."""

    deployments = [
        deployment for deployment in service.get("deployments", []) if isinstance(deployment, dict)
    ]
    primary = next(
        (deployment for deployment in deployments if deployment.get("status") == "PRIMARY"),
        None,
    )
    service_desired = _to_int(service.get("desiredCount"))
    service_running = _to_int(service.get("runningCount"))
    service_task_definition = _to_optional_str(service.get("taskDefinition"))
    primary_task_definition = _to_optional_str(primary.get("taskDefinition") if primary else None)
    primary_desired = _to_optional_int(primary.get("desiredCount") if primary else None)
    primary_running = _to_optional_int(primary.get("runningCount") if primary else None)
    primary_pending = _to_optional_int(primary.get("pendingCount") if primary else None)
    blocking_deployments = tuple(
        _deployment_snapshot(deployment)
        for deployment in deployments
        if deployment is not primary and _deployment_is_active(deployment)
    )

    blocking_detail = _rollout_blocking_detail(
        service_desired=service_desired,
        service_running=service_running,
        service_task_definition=service_task_definition,
        primary=primary,
        primary_task_definition=primary_task_definition,
        primary_desired=primary_desired,
        primary_running=primary_running,
        primary_pending=primary_pending,
        blocking_deployments=blocking_deployments,
        expected_task_definition=expected_task_definition,
    )
    if blocking_detail is None:
        detail = (
            "Expected task definition is the only active deployment serving the full desired count."
        )
        ready = True
    else:
        detail = blocking_detail
        ready = False
    return ServiceRolloutProbeResult(
        ready=ready,
        detail=detail,
        service_desired=service_desired,
        service_running=service_running,
        service_task_definition=service_task_definition,
        primary_task_definition=primary_task_definition,
        primary_desired=primary_desired,
        primary_running=primary_running,
        primary_pending=primary_pending,
        blocking_deployments=blocking_deployments,
    )


def wait_for_service_rollout(
    describe_current_service: Callable[[], dict[str, object]],
    *,
    expected_task_definition: str,
    timeout_seconds: float,
    poll_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> ServiceRolloutWaitResult:
    """Retry service rollout probes until the expected revision is fully serving."""

    deadline = monotonic() + timeout_seconds
    attempts = 0
    last_probe = ServiceRolloutProbeResult(
        ready=False,
        detail="No rollout probes were attempted yet.",
        service_desired=0,
        service_running=0,
        service_task_definition=None,
        primary_task_definition=None,
        primary_desired=None,
        primary_running=None,
        primary_pending=None,
        blocking_deployments=(),
    )
    while monotonic() < deadline:
        attempts += 1
        last_probe = probe_service_rollout(
            describe_current_service(),
            expected_task_definition=expected_task_definition,
        )
        if last_probe.ready:
            return ServiceRolloutWaitResult(status="ok", attempts=attempts, last_probe=last_probe)
        sleep(poll_seconds)
    return ServiceRolloutWaitResult(status="timeout", attempts=attempts, last_probe=last_probe)


def main() -> None:
    """Wait until one ECS service fully serves the expected task definition."""

    parser = argparse.ArgumentParser(description="Wait for one ECS service rollout.")
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--expected-task-definition", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    args = parser.parse_args()

    result = wait_for_service_rollout(
        lambda: describe_service(cluster=args.cluster, service_name=args.service),
        expected_task_definition=args.expected_task_definition,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    print(json.dumps(asdict(result.last_probe), sort_keys=True))
    if result.status != "ok":
        raise SystemExit(1)


def _deployment_is_active(deployment: dict[str, object]) -> bool:
    """Return whether one non-primary deployment still owns work."""

    return any(
        _to_int(deployment.get(key)) > 0 for key in ("desiredCount", "runningCount", "pendingCount")
    )


def _deployment_snapshot(deployment: dict[str, object]) -> dict[str, object]:
    """Return a compact deployment summary for failure payloads."""

    return {
        "id": deployment.get("id"),
        "status": deployment.get("status"),
        "taskDefinition": deployment.get("taskDefinition"),
        "desiredCount": _to_int(deployment.get("desiredCount")),
        "runningCount": _to_int(deployment.get("runningCount")),
        "pendingCount": _to_int(deployment.get("pendingCount")),
    }


def _rollout_blocking_detail(
    *,
    service_desired: int,
    service_running: int,
    service_task_definition: str | None,
    primary: dict[str, object] | None,
    primary_task_definition: str | None,
    primary_desired: int | None,
    primary_running: int | None,
    primary_pending: int | None,
    blocking_deployments: tuple[dict[str, Any], ...],
    expected_task_definition: str,
) -> str | None:
    """Return the current rollout blocker, if one still exists."""

    conditions = (
        ("ECS service desired count is 0.", service_desired <= 0),
        ("ECS service does not report a PRIMARY deployment yet.", primary is None),
        (
            "ECS service desired task definition does not match the expected revision yet.",
            service_task_definition != expected_task_definition,
        ),
        (
            "PRIMARY deployment is not the expected task definition yet.",
            primary_task_definition != expected_task_definition,
        ),
        (
            "PRIMARY deployment does not own the full service desired count yet.",
            primary_desired != service_desired,
        ),
        ("PRIMARY deployment still has pending tasks.", primary_pending != 0),
        ("Older ECS deployments still have active tasks.", bool(blocking_deployments)),
        (
            "Expected task definition is not serving the full desired task count yet.",
            primary_running != service_desired or service_running != service_desired,
        ),
    )
    return next((detail for detail, blocked in conditions if blocked), None)


def _to_int(value: object) -> int:
    return int(value or 0)


def _to_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


if __name__ == "__main__":
    main()
