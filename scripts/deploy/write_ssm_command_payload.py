"""Write one JSON payload for `aws ssm send-command`.

The payload writes a rendered deploy bundle onto the host and then runs the
bundle runner. For rollback, it emits the smaller command set that reactivates
the previous recorded bundle on the host.
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path


def _quote(value: str) -> str:
    return shlex.quote(value)


def _write_file_command(*, relative_path: Path, content: str) -> str:
    sentinel = "__CODEX_DEPLOY_FILE__"
    rendered_content = content if content.endswith("\n") else content + "\n"
    return f"cat > {_quote(relative_path.as_posix())} <<'{sentinel}'\n{rendered_content}{sentinel}"


def _bundle_file_commands(*, bundle_dir: Path, release_root: Path) -> list[str]:
    commands: list[str] = []
    for file_path in sorted(path for path in bundle_dir.rglob("*") if path.is_file()):
        relative = file_path.relative_to(bundle_dir)
        target = release_root / relative
        commands.append(f"mkdir -p {_quote(target.parent.as_posix())}")
        commands.append(
            _write_file_command(
                relative_path=target,
                content=file_path.read_text(encoding="utf-8"),
            )
        )
    return commands


def _deploy_commands(*, bundle_dir: Path, state_dir: Path) -> list[str]:
    host_env_path = bundle_dir / "host.env"
    release_tag = None
    for raw_line in host_env_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("RELEASE_GIT_TAG="):
            release_tag = raw_line.partition("=")[2]
            break
    if not release_tag:
        msg = f"Could not find RELEASE_GIT_TAG in {host_env_path}."
        raise ValueError(msg)

    release_root = state_dir / "releases" / release_tag
    commands = [
        "set -euo pipefail",
        f"mkdir -p {_quote((state_dir / 'releases').as_posix())}",
        f"rm -rf {_quote(release_root.as_posix())}",
        f"mkdir -p {_quote(release_root.as_posix())}",
    ]
    commands.extend(_bundle_file_commands(bundle_dir=bundle_dir, release_root=release_root))
    commands.append(
        "python3 "
        + _quote((release_root / "scripts" / "host_bundle_runner.py").as_posix())
        + " deploy --bundle-dir "
        + _quote(release_root.as_posix())
        + " --state-dir "
        + _quote(state_dir.as_posix())
    )
    return commands


def _rollback_previous_commands(*, state_dir: Path) -> list[str]:
    previous_tag_path = state_dir / "previous_release_tag.txt"
    return [
        "set -euo pipefail",
        f"test -s {_quote(previous_tag_path.as_posix())}",
        "PREVIOUS_RELEASE_TAG=$(cat " + _quote(previous_tag_path.as_posix()) + ")",
        "python3 "
        + _quote((state_dir / "releases").as_posix())
        + '/"${PREVIOUS_RELEASE_TAG}"/scripts/host_bundle_runner.py'
        + " rollback-previous --state-dir "
        + _quote(state_dir.as_posix()),
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write SSM send-command parameters JSON.")
    parser.add_argument("--mode", choices=("deploy", "rollback-previous"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/ikea-agent/deploy"))
    parser.add_argument("--bundle-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    """Write the requested SSM command payload to disk."""

    args = _parse_args()
    if args.mode == "deploy":
        if args.bundle_dir is None:
            raise ValueError("--bundle-dir is required for deploy mode.")
        commands = _deploy_commands(bundle_dir=args.bundle_dir.resolve(), state_dir=args.state_dir)
    else:
        commands = _rollback_previous_commands(state_dir=args.state_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"commands": commands}, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
