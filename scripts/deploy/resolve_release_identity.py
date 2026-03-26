"""Resolve one publishable release identity from a published GitHub release.

This keeps the publish workflow anchored to the immutable GitHub release event
and the checked-in release version instead of trusting mutable pull-request or
branch metadata. The release version comes from `version.txt`, and this helper
proves that the published release event, the checked-out tag, and the current
commit all describe the same release.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.deploy.read_release_version import read_release_version
from scripts.deploy.release_manifest import validate_app_version, validate_git_sha


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    """One validated release identity shared across workflow publication steps."""

    version: str
    git_tag: str
    git_sha: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object in {path}."
        raise TypeError(msg)
    return payload


def _require_object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        msg = f"Expected object field {key!r} in GitHub event payload."
        raise TypeError(msg)
    return value


def _require_string(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"Expected non-empty string field {key!r} in GitHub event payload."
        raise ValueError(msg)
    return value


def _resolve_current_head_sha(head_sha: str | None) -> str:
    if head_sha is not None:
        return validate_git_sha(head_sha)
    git_executable = shutil.which("git")
    if git_executable is None:
        msg = "Could not locate git in PATH while resolving the checked-out release commit."
        raise RuntimeError(msg)
    resolved_sha = subprocess.check_output(  # noqa: S603
        [git_executable, "rev-parse", "HEAD"],
        text=True,
    ).strip()
    return validate_git_sha(resolved_sha)


def resolve_release_identity(
    *,
    event_path: Path,
    version_file: Path,
    head_sha: str | None = None,
) -> ReleaseIdentity:
    """Validate one published GitHub release against the checked-out tagged commit."""

    payload = _read_json_object(event_path)
    action = _require_string(payload, "action")
    if action != "published":
        msg = f"Release publication requires a published release event, found {action!r}."
        raise ValueError(msg)

    release = _require_object(payload, "release")
    release_tag = _require_string(release, "tag_name")

    version = validate_app_version(read_release_version(version_file))
    expected_tag = f"v{version}"
    if release_tag != expected_tag:
        msg = (
            "Published release tag "
            f"{release_tag!r} does not match version.txt tag {expected_tag!r}."
        )
        raise ValueError(msg)
    current_head_sha = _resolve_current_head_sha(head_sha)

    return ReleaseIdentity(
        version=version,
        git_tag=release_tag,
        git_sha=current_head_sha,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve the publishable release identity from a published GitHub release."
    )
    parser.add_argument(
        "--event-path",
        type=Path,
        default=None,
        help="Path to the GitHub Actions event payload JSON.",
    )
    parser.add_argument(
        "--version-file",
        type=Path,
        default=_repo_root() / "version.txt",
        help="Path to the plain semver release version file.",
    )
    parser.add_argument(
        "--head-sha",
        help="Optional checked-out commit SHA override for tests.",
    )
    return parser.parse_args()


def main() -> int:
    """Print the validated release identity as GitHub Actions output lines."""

    args = _parse_args()
    event_path = args.event_path
    if event_path is None:
        github_event_path = os.environ.get("GITHUB_EVENT_PATH")
        if github_event_path is None:
            msg = "GITHUB_EVENT_PATH must be set unless --event-path is provided."
            raise RuntimeError(msg)
        event_path = Path(github_event_path)
    release = resolve_release_identity(
        event_path=event_path,
        version_file=args.version_file,
        head_sha=args.head_sha,
    )
    print(f"version={release.version}")
    print(f"tag={release.git_tag}")
    print(f"git_sha={release.git_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
