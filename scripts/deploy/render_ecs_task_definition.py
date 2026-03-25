"""Render one registerable ECS task definition from a described revision.

AWS `describe-task-definition` returns fields that cannot be fed back into
`register-task-definition` unchanged. This helper strips the read-only fields,
updates one named container image, and applies a small set of environment
overrides so deploy automation can roll forward by immutable image digest
without duplicating the whole task definition in CI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_READ_ONLY_FIELDS = {
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "requiresAttributes",
    "revision",
    "status",
    "taskDefinitionArn",
}
_PLACEHOLDER_COMMAND = ["sh", "-c", "sleep infinity"]


def _load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object in {path}."
        raise TypeError(msg)
    if "taskDefinition" in payload:
        nested = payload["taskDefinition"]
        if not isinstance(nested, dict):
            msg = f"Expected JSON object at taskDefinition in {path}."
            raise TypeError(msg)
        return nested
    return payload


def _parse_set_env(values: list[str]) -> dict[str, str]:
    env_updates: dict[str, str] = {}
    for raw_value in values:
        key, separator, value = raw_value.partition("=")
        if not separator or not key:
            msg = f"Expected KEY=VALUE for --set-env, found {raw_value!r}."
            raise ValueError(msg)
        env_updates[key] = value
    return env_updates


def _container_definitions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    container_definitions = payload.get("containerDefinitions")
    if not isinstance(container_definitions, list):
        msg = "Expected task definition payload to contain containerDefinitions."
        raise TypeError(msg)
    normalized: list[dict[str, Any]] = []
    for container in container_definitions:
        if not isinstance(container, dict):
            msg = "Expected every container definition to be a JSON object."
            raise TypeError(msg)
        normalized.append(container)
    return normalized


def _render_container(
    container: dict[str, Any],
    *,
    container_name: str,
    image: str,
    env_updates: dict[str, str],
) -> dict[str, Any]:
    if container.get("name") != container_name:
        return container

    rendered = dict(container)
    rendered["image"] = image

    existing_env = rendered.get("environment", [])
    if not isinstance(existing_env, list):
        msg = f"Expected environment list for container {container_name!r}."
        raise TypeError(msg)

    env_map: dict[str, str] = {}
    for entry in existing_env:
        if not isinstance(entry, dict):
            msg = f"Expected env entry object for container {container_name!r}."
            raise TypeError(msg)
        name = entry.get("name")
        value = entry.get("value")
        if isinstance(name, str) and isinstance(value, str):
            env_map[name] = value

    env_map.update(env_updates)
    rendered["environment"] = [
        {"name": name, "value": value} for name, value in sorted(env_map.items())
    ]
    command = rendered.get("command")
    if command == _PLACEHOLDER_COMMAND:
        rendered.pop("command", None)
    return rendered


def render_task_definition(
    *,
    payload: dict[str, Any],
    container_name: str,
    image: str,
    env_updates: dict[str, str],
) -> dict[str, Any]:
    """Strip read-only AWS fields and apply image/env overrides."""

    rendered = {key: value for key, value in payload.items() if key not in _READ_ONLY_FIELDS}
    container_definitions = _container_definitions(rendered)
    rendered["containerDefinitions"] = [
        _render_container(
            container,
            container_name=container_name,
            image=image,
            env_updates=env_updates,
        )
        for container in container_definitions
    ]
    if not any(
        container.get("name") == container_name for container in rendered["containerDefinitions"]
    ):
        msg = f"Container {container_name!r} not present in task definition."
        raise ValueError(msg)
    return rendered


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a registerable ECS task definition.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--set-env",
        action="append",
        default=[],
        help="Environment override in KEY=VALUE form. May be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    """Write the rendered task definition JSON to disk."""

    args = _parse_args()
    rendered = render_task_definition(
        payload=_load_payload(args.input),
        container_name=args.container,
        image=args.image,
        env_updates=_parse_set_env(args.set_env),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rendered, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
