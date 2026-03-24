"""Typed attachment storage backends and durable locator helpers.

This module keeps the browser contract stable while letting durable asset rows
store opaque storage locators instead of assuming container-local filesystem
paths forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

_LOCAL_LOCATOR_PREFIX = "local://"
_S3_LOCATOR_PREFIX = "s3://"


class AttachmentStorageError(RuntimeError):
    """Raised when attachment bytes cannot be persisted or resolved."""


@dataclass(frozen=True, slots=True)
class SavedAttachmentObject:
    """Result of one storage write including durable locator and local materialization."""

    locator: str
    materialized_path: Path


@dataclass(frozen=True, slots=True)
class StorageObjectDescriptor:
    """Stable metadata used to derive object keys across storage backends."""

    attachment_id: str
    thread_id: str
    run_id: str | None
    file_name: str
    mime_type: str
    kind: str


@dataclass(frozen=True, slots=True)
class LocalStorageLocator:
    """Locator stored for bytes rooted under the configured artifact directory."""

    relative_path: PurePosixPath


@dataclass(frozen=True, slots=True)
class S3StorageLocator:
    """Locator stored for bytes rooted in one private S3 bucket."""

    bucket: str
    key: str


@dataclass(frozen=True, slots=True)
class LegacyPathStorageLocator:
    """Compatibility shim for older absolute-path asset rows."""

    path: Path


StorageLocator = LocalStorageLocator | S3StorageLocator | LegacyPathStorageLocator


class AttachmentStorageBackend(Protocol):
    """Backend contract used by the attachment store."""

    def save_attachment(
        self,
        *,
        descriptor: StorageObjectDescriptor,
        content: bytes,
    ) -> SavedAttachmentObject:
        """Persist bytes for one attachment and return its durable locator."""

    def materialize_locator(
        self,
        *,
        locator: str,
        attachment_id: str,
        file_name: str | None,
        mime_type: str,
    ) -> Path:
        """Resolve one durable locator to a readable local path."""

    def find_local_path(self, *, attachment_id: str) -> Path | None:
        """Resolve a legacy local-only attachment id when no DB row exists."""


def parse_storage_locator(locator: str) -> StorageLocator:
    """Parse one durable storage locator, keeping legacy paths readable."""

    if locator.startswith(_LOCAL_LOCATOR_PREFIX):
        relative_path = locator.removeprefix(_LOCAL_LOCATOR_PREFIX).lstrip("/")
        return LocalStorageLocator(relative_path=PurePosixPath(relative_path))
    if locator.startswith(_S3_LOCATOR_PREFIX):
        remainder = locator.removeprefix(_S3_LOCATOR_PREFIX)
        bucket, separator, key = remainder.partition("/")
        if not bucket or not separator or not key:
            msg = f"Invalid S3 storage locator: {locator}"
            raise AttachmentStorageError(msg)
        return S3StorageLocator(bucket=bucket, key=key)
    return LegacyPathStorageLocator(path=Path(locator).expanduser())


def build_local_storage_locator(relative_path: PurePosixPath) -> str:
    """Return the durable locator used for local artifact storage rows."""

    return f"{_LOCAL_LOCATOR_PREFIX}{relative_path.as_posix()}"


def build_s3_storage_locator(*, bucket: str, key: str) -> str:
    """Return the durable locator used for private S3 artifact storage rows."""

    return f"{_S3_LOCATOR_PREFIX}{bucket}/{key}"


def build_attachment_object_key(descriptor: StorageObjectDescriptor) -> PurePosixPath:
    """Return the storage-object key shared by local and S3 backends."""

    suffix = Path(descriptor.file_name).suffix
    filename = f"{descriptor.attachment_id}{suffix}"
    thread_segment = descriptor.thread_id or "anonymous-thread"
    if descriptor.kind == "user_upload":
        return PurePosixPath("attachments") / "user-upload" / thread_segment / filename
    if descriptor.kind in {"floor_plan_png", "floor_plan_svg"}:
        return PurePosixPath("attachments") / "floor-plan" / thread_segment / filename
    run_segment = descriptor.run_id or "none"
    return PurePosixPath("attachments") / "generated" / thread_segment / run_segment / filename


class LocalAttachmentStorageBackend:
    """Persist private attachment bytes under the configured local artifact root."""

    def __init__(self, *, root_dir: Path) -> None:
        """Store the local root used for artifact writes and reads."""

        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def save_attachment(
        self,
        *,
        descriptor: StorageObjectDescriptor,
        content: bytes,
    ) -> SavedAttachmentObject:
        """Write attachment bytes under the structured local object key."""

        relative_path = build_attachment_object_key(descriptor)
        path = self._root_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return SavedAttachmentObject(
            locator=build_local_storage_locator(relative_path),
            materialized_path=path,
        )

    def materialize_locator(
        self,
        *,
        locator: str,
        attachment_id: str,
        file_name: str | None,
        mime_type: str,
    ) -> Path:
        """Resolve local or legacy locators to a readable path."""

        del attachment_id, file_name, mime_type
        parsed = parse_storage_locator(locator)
        if isinstance(parsed, LegacyPathStorageLocator):
            return parsed.path
        if isinstance(parsed, S3StorageLocator):
            msg = f"Local attachment storage cannot resolve S3 locator: {locator}"
            raise AttachmentStorageError(msg)
        return self._root_dir / parsed.relative_path

    def find_local_path(self, *, attachment_id: str) -> Path | None:
        """Fallback lookup used by local tests that do not wire persistence."""

        return next(self._root_dir.rglob(f"{attachment_id}.*"), None)


class S3AttachmentStorageBackend:
    """Persist private attachment bytes to S3 while materializing reads locally."""

    def __init__(
        self,
        *,
        root_dir: Path,
        bucket: str,
        prefix: str | None,
        region_name: str | None = None,
    ) -> None:
        """Create the runtime S3 backend with a small local read cache."""

        self._root_dir = root_dir
        self._bucket = bucket
        self._prefix = PurePosixPath(prefix.strip("/")) if prefix and prefix.strip("/") else None
        self._materialized_root = root_dir / "_materialized"
        self._materialized_root.mkdir(parents=True, exist_ok=True)

        self._client = boto3.client("s3", region_name=region_name)

    def save_attachment(
        self,
        *,
        descriptor: StorageObjectDescriptor,
        content: bytes,
    ) -> SavedAttachmentObject:
        """Upload bytes to S3 and keep a local copy for immediate reuse."""

        relative_key = build_attachment_object_key(descriptor)
        key = self._apply_prefix(relative_key)
        self._client.put_object(
            Body=content,
            Bucket=self._bucket,
            Key=key,
            ContentType=descriptor.mime_type,
        )
        materialized_path = self._materialized_path(
            attachment_id=descriptor.attachment_id,
            file_name=descriptor.file_name,
            mime_type=descriptor.mime_type,
        )
        materialized_path.parent.mkdir(parents=True, exist_ok=True)
        materialized_path.write_bytes(content)
        return SavedAttachmentObject(
            locator=build_s3_storage_locator(bucket=self._bucket, key=key),
            materialized_path=materialized_path,
        )

    def materialize_locator(
        self,
        *,
        locator: str,
        attachment_id: str,
        file_name: str | None,
        mime_type: str,
    ) -> Path:
        """Download one private object when needed and return a local cache path."""

        parsed = parse_storage_locator(locator)
        if isinstance(parsed, LegacyPathStorageLocator):
            return parsed.path
        if isinstance(parsed, LocalStorageLocator):
            return self._root_dir / parsed.relative_path
        materialized_path = self._materialized_path(
            attachment_id=attachment_id,
            file_name=file_name,
            mime_type=mime_type,
        )
        if materialized_path.exists():
            return materialized_path

        try:
            response = self._client.get_object(Bucket=parsed.bucket, Key=parsed.key)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchBucket", "NoSuchKey"}:
                raise FileNotFoundError(locator) from exc
            raise
        body = response["Body"].read()
        materialized_path.parent.mkdir(parents=True, exist_ok=True)
        materialized_path.write_bytes(body)
        return materialized_path

    def find_local_path(self, *, attachment_id: str) -> Path | None:
        """S3-backed storage relies on durable metadata and does not support glob fallback."""

        del attachment_id
        return None

    def _apply_prefix(self, relative_key: PurePosixPath) -> str:
        if self._prefix is None:
            return relative_key.as_posix()
        return (self._prefix / relative_key).as_posix()

    def _materialized_path(
        self,
        *,
        attachment_id: str,
        file_name: str | None,
        mime_type: str,
    ) -> Path:
        suffix = Path(file_name).suffix if file_name else _suffix_for_mime_type(mime_type)
        return self._materialized_root / f"{attachment_id}{suffix}"


def build_attachment_storage_backend(
    *,
    root_dir: Path,
    backend_kind: str,
    s3_bucket: str | None,
    s3_prefix: str | None,
    s3_region: str | None,
) -> AttachmentStorageBackend:
    """Build the configured storage backend for app and CLI runtime entrypoints."""

    if backend_kind == "s3":
        if not s3_bucket:
            msg = "ARTIFACT_S3_BUCKET is required when ARTIFACT_STORAGE_BACKEND=s3."
            raise ValueError(msg)
        return S3AttachmentStorageBackend(
            root_dir=root_dir,
            bucket=s3_bucket,
            prefix=s3_prefix,
            region_name=s3_region,
        )
    return LocalAttachmentStorageBackend(root_dir=root_dir)


def _suffix_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/png":
        return ".png"
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    if mime_type == "image/svg+xml":
        return ".svg"
    return ".bin"
