from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from scripts.deploy.ecs_release_deploy import (
    EcsDeployContext,
    ReleaseDeployRequest,
    ReleaseDeployResult,
    deploy_release,
    resolve_deploy_context,
    run_one_off_backend_task_to_completion,
)

JsonHandler = Callable[[tuple[str, ...]], object]


@dataclass
class StubAwsCli:
    json_calls: list[tuple[str, ...]] = field(default_factory=list)
    text_calls: list[tuple[str, ...]] = field(default_factory=list)
    call_calls: list[tuple[str, ...]] = field(default_factory=list)
    json_handler: JsonHandler | None = None

    def json(self, *args: str) -> object:
        self.json_calls.append(args)
        if self.json_handler is None:
            msg = f"Unexpected json call: {args!r}"
            raise AssertionError(msg)
        return self.json_handler(args)

    def text(self, *args: str) -> str:
        self.text_calls.append(args)
        msg = f"Unexpected text call: {args!r}"
        raise AssertionError(msg)

    def call(self, *args: str) -> None:
        self.call_calls.append(args)


@dataclass
class DeployReleaseHarness:
    events: list[tuple[str, str]] = field(default_factory=list)
    registered_task_definitions: list[dict[str, Any]] = field(default_factory=list)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.describe_service",
            self.describe_service,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.resolve_deploy_context",
            self.resolve_context,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.describe_task_definition",
            self.describe_task_definition,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.register_task_definition",
            self.register_task_definition,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.run_one_off_backend_task_to_completion",
            self.run_one_off_backend_task_to_completion,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.update_service",
            self.update_service,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.wait_for_backend_service_rollout",
            self.wait_for_backend_service_rollout,
        )
        monkeypatch.setattr(
            "scripts.deploy.ecs_release_deploy.wait_for_ui_service_stable",
            self.wait_for_ui_service_stable,
        )

    def describe_service(
        self,
        *,
        cluster: str,
        service_name: str,
        aws_cli: object,
    ) -> dict[str, Any]:
        del aws_cli
        self.events.append(("describe_service", service_name))
        assert cluster == "cluster-1"
        return {"serviceName": service_name}

    def resolve_context(
        self,
        *,
        backend_service: dict[str, Any],
        ui_service: dict[str, Any],
        aws_cli: object,
    ) -> EcsDeployContext:
        del aws_cli
        assert backend_service["serviceName"] == "backend-service"
        assert ui_service["serviceName"] == "ui-service"
        self.events.append(("resolve_context", "ok"))
        return EcsDeployContext(
            backend_task_definition_arn="backend:current",
            ui_task_definition_arn="ui:current",
            backend_network_configuration={"awsvpcConfiguration": {"subnets": ["subnet-a"]}},
            alb_dns_name="alb.example.internal",
        )

    def describe_task_definition(
        self,
        *,
        task_definition_arn: str,
        aws_cli: object,
    ) -> dict[str, Any]:
        del aws_cli
        self.events.append(("describe_task_definition", task_definition_arn))
        is_backend = task_definition_arn.startswith("backend")
        family = "ikea-agent-dev-backend" if is_backend else "ikea-agent-dev-ui"
        name = "backend" if is_backend else "ui"
        return {
            "family": family,
            "containerDefinitions": [
                {
                    "name": name,
                    "image": "placeholder",
                    "environment": [{"name": "APP_ENV", "value": "dev"}],
                }
            ],
        }

    def register_task_definition(
        self,
        *,
        task_definition: dict[str, Any],
        aws_cli: object,
    ) -> str:
        del aws_cli
        self.registered_task_definitions.append(task_definition)
        family = str(task_definition["family"])
        self.events.append(("register_task_definition", family))
        return f"{family}:next"

    def run_one_off_backend_task_to_completion(
        self,
        *,
        cluster: str,
        task_definition_arn: str,
        network_configuration: dict[str, Any],
        command: list[str],
        aws_cli: object,
    ) -> str:
        del aws_cli
        assert cluster == "cluster-1"
        assert task_definition_arn == "ikea-agent-dev-backend:next"
        assert network_configuration == {"awsvpcConfiguration": {"subnets": ["subnet-a"]}}
        self.events.append(("run_one_off_backend_task", " ".join(command)))
        return "task-123"

    def update_service(
        self,
        *,
        cluster: str,
        service_name: str,
        task_definition_arn: str,
        desired_count: int,
        aws_cli: object,
    ) -> None:
        del aws_cli
        assert cluster == "cluster-1"
        self.events.append(
            ("update_service", f"{service_name}:{task_definition_arn}:{desired_count}")
        )

    def wait_for_backend_service_rollout(
        self,
        *,
        cluster: str,
        service_name: str,
        task_definition_arn: str,
        timeout_seconds: float,
        poll_seconds: float,
        aws_cli: object,
        sleep: object,
        monotonic: object,
    ) -> None:
        del aws_cli, monotonic, sleep
        assert cluster == "cluster-1"
        assert timeout_seconds == 900.0
        assert poll_seconds == 15.0
        self.events.append(("wait_for_backend_rollout", f"{service_name}:{task_definition_arn}"))

    def wait_for_ui_service_stable(
        self,
        *,
        cluster: str,
        service_name: str,
        aws_cli: object,
    ) -> None:
        del aws_cli
        assert cluster == "cluster-1"
        self.events.append(("wait_for_ui_service_stable", service_name))


def test_resolve_deploy_context_extracts_task_definitions_network_and_alb() -> None:
    backend_service = {
        "taskDefinition": "backend:12",
        "loadBalancers": [{"targetGroupArn": "tg-123"}],
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": ["subnet-a", "subnet-b"],
                "securityGroups": ["sg-backend"],
                "assignPublicIp": "ENABLED",
            }
        },
    }
    ui_service = {"taskDefinition": "ui:34"}

    def _json_handler(args: tuple[str, ...]) -> object:
        if args == (
            "elbv2",
            "describe-target-groups",
            "--target-group-arns",
            "tg-123",
        ):
            return {"TargetGroups": [{"LoadBalancerArns": ["alb-123"]}]}
        if args == (
            "elbv2",
            "describe-load-balancers",
            "--load-balancer-arns",
            "alb-123",
        ):
            return {"LoadBalancers": [{"DNSName": "alb.example.internal"}]}
        msg = f"Unexpected json call: {args!r}"
        raise AssertionError(msg)

    aws_cli = StubAwsCli(json_handler=_json_handler)

    context = resolve_deploy_context(
        backend_service=backend_service,
        ui_service=ui_service,
        aws_cli=aws_cli,  # type: ignore[arg-type]
    )

    assert context == EcsDeployContext(
        backend_task_definition_arn="backend:12",
        ui_task_definition_arn="ui:34",
        backend_network_configuration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-a", "subnet-b"],
                "securityGroups": ["sg-backend"],
                "assignPublicIp": "ENABLED",
            }
        },
        alb_dns_name="alb.example.internal",
    )


def test_run_one_off_backend_task_to_completion_raises_for_nonzero_exit_code() -> None:
    def _json_handler(args: tuple[str, ...]) -> object:
        if args[:2] == ("ecs", "run-task"):
            return {"tasks": [{"taskArn": "task-123"}], "failures": []}
        if args[:2] == ("ecs", "describe-tasks"):
            return {
                "tasks": [
                    {
                        "taskArn": "task-123",
                        "containers": [{"name": "backend", "exitCode": 1}],
                    }
                ]
            }
        msg = f"Unexpected json call: {args!r}"
        raise AssertionError(msg)

    aws_cli = StubAwsCli(json_handler=_json_handler)

    with pytest.raises(RuntimeError, match="failed with exit code 1"):
        run_one_off_backend_task_to_completion(
            cluster="cluster-1",
            task_definition_arn="backend:99",
            network_configuration={"awsvpcConfiguration": {"subnets": ["subnet-a"]}},
            command=["python", "-m", "scripts.deploy.apply_migrations"],
            aws_cli=aws_cli,  # type: ignore[arg-type]
        )

    assert aws_cli.call_calls == [
        ("ecs", "wait", "tasks-stopped", "--cluster", "cluster-1", "--tasks", "task-123")
    ]


def test_deploy_release_preserves_backend_then_ui_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ReleaseDeployRequest(
        cluster_name="cluster-1",
        backend_service_name="backend-service",
        ui_service_name="ui-service",
        app_version="1.2.3",
        backend_image_ref="backend@sha256:abcd",
        ui_image_ref="ui@sha256:efgh",
        postgres_seed_version="seed-123",
        public_app_base_url="https://designagent.talperry.com",
    )
    harness = DeployReleaseHarness()

    def _smoke_check(base_url: str) -> None:
        harness.events.append(("smoke_check", base_url))

    harness.install(monkeypatch)

    result = deploy_release(
        request,
        aws_cli=object(),  # type: ignore[arg-type]
        smoke_checker=_smoke_check,  # type: ignore[arg-type]
    )

    assert result == ReleaseDeployResult(
        alb_dns_name="alb.example.internal",
        backend_task_definition_arn="ikea-agent-dev-backend:next",
        ui_task_definition_arn="ikea-agent-dev-ui:next",
        backend_service_name="backend-service",
        ui_service_name="ui-service",
        public_app_base_url="https://designagent.talperry.com",
    )
    assert harness.events == [
        ("describe_service", "backend-service"),
        ("describe_service", "ui-service"),
        ("resolve_context", "ok"),
        ("describe_task_definition", "backend:current"),
        ("register_task_definition", "ikea-agent-dev-backend"),
        ("run_one_off_backend_task", "python -m scripts.deploy.apply_migrations"),
        (
            "run_one_off_backend_task",
            "python -m scripts.deploy.verify_seed_state --expected-postgres-seed-version seed-123",
        ),
        ("update_service", "backend-service:ikea-agent-dev-backend:next:1"),
        ("wait_for_backend_rollout", "backend-service:ikea-agent-dev-backend:next"),
        ("describe_task_definition", "ui:current"),
        ("register_task_definition", "ikea-agent-dev-ui"),
        ("update_service", "ui-service:ikea-agent-dev-ui:next:1"),
        ("wait_for_ui_service_stable", "ui-service"),
        ("smoke_check", "https://designagent.talperry.com"),
    ]

    backend_environment = harness.registered_task_definitions[0]["containerDefinitions"][0][
        "environment"
    ]
    ui_environment = harness.registered_task_definitions[1]["containerDefinitions"][0][
        "environment"
    ]
    assert {"name": "LOGFIRE_SERVICE_VERSION", "value": "1.2.3"} in backend_environment
    assert {"name": "APP_RELEASE_VERSION", "value": "1.2.3"} in ui_environment
    assert {"name": "PY_AG_UI_URL", "value": "http://alb.example.internal/ag-ui/"} in ui_environment
    assert {
        "name": "BACKEND_PROXY_BASE_URL",
        "value": "http://alb.example.internal/",
    } in ui_environment
