from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.render_ecs_task_definition import (
    main as render_ecs_task_definition_main,
)
from scripts.deploy.render_ecs_task_definition import (
    render_task_definition,
)


def _base_task_definition() -> dict[str, object]:
    return {
        "taskDefinitionArn": "arn:aws:ecs:eu-central-1:046673074482:task-definition/backend:3",
        "family": "ikea-agent-dev-backend",
        "revision": 3,
        "status": "ACTIVE",
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "512",
        "memory": "1024",
        "executionRoleArn": "arn:aws:iam::046673074482:role/ikea-agent-dev-ecs-execution",
        "taskRoleArn": "arn:aws:iam::046673074482:role/ikea-agent-dev-backend-task",
        "containerDefinitions": [
            {
                "name": "backend",
                "image": "public.ecr.aws/docker/library/busybox:stable",
                "environment": [
                    {"name": "APP_ENV", "value": "dev"},
                    {"name": "LOGFIRE_SERVICE_VERSION", "value": "bootstrap"},
                ],
            }
        ],
        "requiresAttributes": [{"name": "com.amazonaws.ecs.capability.execution-role-ecr-pull"}],
        "registeredAt": "2026-03-25T00:00:00Z",
        "registeredBy": "arn:aws:iam::046673074482:user/example",
    }


def test_render_task_definition_strips_read_only_fields_and_updates_values() -> None:
    rendered = render_task_definition(
        payload=_base_task_definition(),
        container_name="backend",
        image="123456789012.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend@sha256:abcd",
        env_updates={
            "LOGFIRE_SERVICE_VERSION": "1.2.3",
            "IMAGE_SERVICE_BASE_URL": "https://designagent.talperry.com/static/product-images",
        },
    )

    assert "taskDefinitionArn" not in rendered
    assert "revision" not in rendered
    assert "status" not in rendered
    container = rendered["containerDefinitions"][0]
    assert container["image"].endswith("@sha256:abcd")
    assert container["environment"] == [
        {"name": "APP_ENV", "value": "dev"},
        {
            "name": "IMAGE_SERVICE_BASE_URL",
            "value": "https://designagent.talperry.com/static/product-images",
        },
        {"name": "LOGFIRE_SERVICE_VERSION", "value": "1.2.3"},
    ]


def test_render_task_definition_requires_named_container() -> None:
    with pytest.raises(ValueError, match="not present"):
        render_task_definition(
            payload=_base_task_definition(),
            container_name="ui",
            image="example",
            env_updates={},
        )


def test_render_ecs_task_definition_main_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps({"taskDefinition": _base_task_definition()}), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "render_ecs_task_definition.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--container",
            "backend",
            "--image",
            "example.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend@sha256:efgh",
            "--set-env",
            "LOGFIRE_SERVICE_VERSION=2.0.0",
        ],
    )

    assert render_ecs_task_definition_main() == 0

    rendered = json.loads(output_path.read_text(encoding="utf-8"))
    assert rendered["containerDefinitions"][0]["image"].endswith("@sha256:efgh")
