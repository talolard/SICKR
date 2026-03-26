from __future__ import annotations

from scripts.deploy.wait_for_ecs_service_rollout import (
    ServiceRolloutProbeResult,
    probe_service_rollout,
    wait_for_service_rollout,
)


def test_probe_service_rollout_accepts_expected_primary_revision() -> None:
    service = _service_payload(
        deployments=[
            _deployment(
                status="PRIMARY",
                task_definition="td:new",
                desired_count=1,
                running_count=1,
                pending_count=0,
            )
        ],
        task_definition="td:new",
        desired_count=1,
        running_count=1,
    )

    result = probe_service_rollout(service, expected_task_definition="td:new")

    assert result.ready is True
    assert result.blocking_deployments == ()


def test_probe_service_rollout_rejects_zero_desired_primary() -> None:
    service = _service_payload(
        deployments=[
            _deployment(
                status="PRIMARY",
                task_definition="td:new",
                desired_count=0,
                running_count=0,
                pending_count=0,
            ),
            _deployment(
                status="ACTIVE",
                task_definition="td:old",
                desired_count=1,
                running_count=1,
                pending_count=0,
            ),
        ],
        task_definition="td:new",
        desired_count=1,
        running_count=1,
    )

    result = probe_service_rollout(service, expected_task_definition="td:new")

    assert result.ready is False
    assert "full service desired count" in result.detail


def test_probe_service_rollout_rejects_active_old_deployments() -> None:
    service = _service_payload(
        deployments=[
            _deployment(
                status="PRIMARY",
                task_definition="td:new",
                desired_count=1,
                running_count=1,
                pending_count=0,
            ),
            _deployment(
                status="ACTIVE",
                task_definition="td:old",
                desired_count=0,
                running_count=1,
                pending_count=0,
            ),
        ],
        task_definition="td:new",
        desired_count=1,
        running_count=2,
    )

    result = probe_service_rollout(service, expected_task_definition="td:new")

    assert result.ready is False
    assert "Older ECS deployments" in result.detail
    assert result.blocking_deployments[0]["taskDefinition"] == "td:old"


def test_wait_for_service_rollout_retries_until_probe_succeeds() -> None:
    attempts = iter(
        [
            ServiceRolloutProbeResult(
                ready=False,
                detail="still draining",
                service_desired=1,
                service_running=2,
                service_task_definition="td:new",
                primary_task_definition="td:new",
                primary_desired=1,
                primary_running=1,
                primary_pending=0,
                blocking_deployments=(
                    {
                        "id": "old",
                        "status": "ACTIVE",
                        "taskDefinition": "td:old",
                        "desiredCount": 0,
                        "runningCount": 1,
                        "pendingCount": 0,
                    },
                ),
            ),
            ServiceRolloutProbeResult(
                ready=True,
                detail="ready",
                service_desired=1,
                service_running=1,
                service_task_definition="td:new",
                primary_task_definition="td:new",
                primary_desired=1,
                primary_running=1,
                primary_pending=0,
                blocking_deployments=(),
            ),
        ]
    )
    current_time = 0.0

    def _describe() -> dict[str, object]:
        probe = next(attempts)
        return _service_payload(
            deployments=[
                _deployment(
                    status="PRIMARY",
                    task_definition=probe.primary_task_definition or "td:new",
                    desired_count=probe.primary_desired or 0,
                    running_count=probe.primary_running or 0,
                    pending_count=probe.primary_pending or 0,
                ),
                *[
                    _deployment(
                        status=str(blocking["status"]),
                        task_definition=str(blocking["taskDefinition"]),
                        desired_count=int(blocking["desiredCount"]),
                        running_count=int(blocking["runningCount"]),
                        pending_count=int(blocking["pendingCount"]),
                    )
                    for blocking in probe.blocking_deployments
                ],
            ],
            task_definition=probe.service_task_definition or "td:new",
            desired_count=probe.service_desired,
            running_count=probe.service_running,
        )

    def _monotonic() -> float:
        nonlocal current_time
        value = current_time
        current_time += 1.0
        return value

    result = wait_for_service_rollout(
        _describe,
        expected_task_definition="td:new",
        timeout_seconds=10.0,
        poll_seconds=0.0,
        sleep=lambda _seconds: None,
        monotonic=_monotonic,
    )

    assert result.status == "ok"
    assert result.attempts == 2
    assert result.last_probe.ready is True
    assert "only active deployment" in result.last_probe.detail


def _service_payload(
    *,
    deployments: list[dict[str, object]],
    task_definition: str,
    desired_count: int,
    running_count: int,
) -> dict[str, object]:
    return {
        "deployments": deployments,
        "taskDefinition": task_definition,
        "desiredCount": desired_count,
        "runningCount": running_count,
    }


def _deployment(
    *,
    status: str,
    task_definition: str,
    desired_count: int,
    running_count: int,
    pending_count: int,
) -> dict[str, object]:
    return {
        "id": f"{status.lower()}-{task_definition}",
        "status": status,
        "taskDefinition": task_definition,
        "desiredCount": desired_count,
        "runningCount": running_count,
        "pendingCount": pending_count,
    }
