"""Shared release-manifest validation and serialization helpers.

The release manifest is the deploy artifact contract between image publication
and host deployment. Build, publish, deploy, and rollback scripts should all
reuse this module instead of reparsing the manifest ad hoc.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ImageManifest:
    """Pinned release metadata for one deployable image."""

    repository: str
    version_tag: str
    commit_tag: str
    digest: str
    image_ref: str
    digest_ref: str


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """Top-level release record shared between publish and deploy automation."""

    schema_version: int
    app_version: str
    git_tag: str
    git_sha: str
    ui_image: ImageManifest
    backend_image: ImageManifest


def validate_app_version(app_version: str) -> str:
    """Return one validated plain semantic version string."""

    if not _SEMVER_RE.fullmatch(app_version):
        msg = f"Expected plain semver for app_version, found {app_version!r}."
        raise ValueError(msg)
    return app_version


def validate_git_tag(app_version: str, git_tag: str) -> str:
    """Return one validated Git tag for the given application version."""

    expected_tag = f"v{app_version}"
    if git_tag != expected_tag:
        msg = f"Expected git_tag {expected_tag!r}, found {git_tag!r}."
        raise ValueError(msg)
    return git_tag


def validate_git_sha(git_sha: str) -> str:
    """Return one normalized release commit SHA."""

    normalized_sha = git_sha.lower()
    if not _SHA_RE.fullmatch(normalized_sha):
        msg = f"Expected 7-40 lowercase hex characters for git_sha, found {git_sha!r}."
        raise ValueError(msg)
    return normalized_sha


def validate_digest(digest: str) -> str:
    """Return one normalized OCI image digest."""

    normalized_digest = digest.lower()
    if not _DIGEST_RE.fullmatch(normalized_digest):
        msg = f"Expected OCI sha256 digest, found {digest!r}."
        raise ValueError(msg)
    return normalized_digest


def build_image_manifest(
    *,
    repository: str,
    app_version: str,
    git_sha: str,
    digest: str,
) -> ImageManifest:
    """Construct one validated image manifest."""

    version_tag = f"v{app_version}"
    commit_tag = f"sha-{git_sha}"
    normalized_digest = validate_digest(digest)
    return ImageManifest(
        repository=repository,
        version_tag=version_tag,
        commit_tag=commit_tag,
        digest=normalized_digest,
        image_ref=f"{repository}:{version_tag}",
        digest_ref=f"{repository}@{normalized_digest}",
    )


def create_release_manifest(
    *,
    app_version: str,
    git_tag: str,
    git_sha: str,
    ui_repository: str,
    ui_digest: str,
    backend_repository: str,
    backend_digest: str,
) -> ReleaseManifest:
    """Construct one validated release manifest."""

    normalized_version = validate_app_version(app_version)
    normalized_tag = validate_git_tag(normalized_version, git_tag)
    normalized_sha = validate_git_sha(git_sha)
    return ReleaseManifest(
        schema_version=1,
        app_version=normalized_version,
        git_tag=normalized_tag,
        git_sha=normalized_sha,
        ui_image=build_image_manifest(
            repository=ui_repository,
            app_version=normalized_version,
            git_sha=normalized_sha,
            digest=ui_digest,
        ),
        backend_image=build_image_manifest(
            repository=backend_repository,
            app_version=normalized_version,
            git_sha=normalized_sha,
            digest=backend_digest,
        ),
    )


def read_release_manifest(path: Path) -> ReleaseManifest:
    """Load and validate one release manifest from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        msg = f"Expected schema_version 1 in {path}, found {payload.get('schema_version')!r}."
        raise ValueError(msg)

    return create_release_manifest(
        app_version=str(payload["app_version"]),
        git_tag=str(payload["git_tag"]),
        git_sha=str(payload["git_sha"]),
        ui_repository=str(payload["ui_image"]["repository"]),
        ui_digest=str(payload["ui_image"]["digest"]),
        backend_repository=str(payload["backend_image"]["repository"]),
        backend_digest=str(payload["backend_image"]["digest"]),
    )


def write_release_manifest(path: Path, manifest: ReleaseManifest) -> None:
    """Persist one validated release manifest to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
