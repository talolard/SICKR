"""Attachment storage primitives for chat image uploads."""

from __future__ import annotations

import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ikea_agent.chat_app.attachment_storage import (
    AttachmentStorageBackend,
    LocalAttachmentStorageBackend,
    StorageObjectDescriptor,
)
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.shared.types import AttachmentRef


@dataclass(frozen=True, slots=True)
class StoredAttachment:
    """Concrete attachment metadata with a readable local materialization path."""

    ref: AttachmentRef
    path: Path
    storage_locator: str


class AttachmentContextError(ValueError):
    """Raised when attachment persistence is attempted without durable identity."""


class AttachmentStore:
    """Attachment store keyed by stable ids with pluggable durable storage."""

    _anonymous_thread_id = "anonymous-thread"
    _room_id_var: ContextVar[str | None]
    _thread_id_var: ContextVar[str | None]
    _run_id_var: ContextVar[str | None]

    def __init__(
        self,
        root_dir: Path,
        *,
        asset_repository: AssetRepository | None = None,
        storage_backend: AttachmentStorageBackend | None = None,
    ) -> None:
        """Create the store with a persistent root directory."""

        self._root_dir = root_dir
        self._asset_repository = asset_repository
        self._storage_backend = (
            LocalAttachmentStorageBackend(root_dir=root_dir)
            if storage_backend is None
            else storage_backend
        )
        self._room_id_var = ContextVar("attachment_store_room_id", default=None)
        self._thread_id_var = ContextVar("attachment_store_thread_id", default=None)
        self._run_id_var = ContextVar("attachment_store_run_id", default=None)

    @property
    def requires_persistence_context(self) -> bool:
        """Return whether uploads must carry explicit durable room/thread identity."""

        return self._asset_repository is not None

    @contextmanager
    def bind_context(
        self,
        *,
        room_id: str | None = None,
        thread_id: str,
        run_id: str | None,
    ) -> Generator[None]:
        """Bind thread/run context for async request-local artifact persistence."""

        room_token = self._room_id_var.set(self._normalize_optional_room_id(room_id))
        thread_token = self._thread_id_var.set(self._normalize_thread_id(thread_id))
        run_token = self._run_id_var.set(run_id)
        try:
            yield
        finally:
            self._room_id_var.reset(room_token)
            self._thread_id_var.reset(thread_token)
            self._run_id_var.reset(run_token)

    def save_image_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str | None,
        room_id: str | None = None,
        thread_id: str | None = None,
        run_id: str | None = None,
        created_by_tool: str | None = None,
        kind: str = "attachment",
    ) -> StoredAttachment:
        """Persist one image and return a stable attachment reference."""

        return self.save_bytes(
            content=content,
            mime_type=mime_type,
            filename=filename,
            room_id=room_id,
            thread_id=thread_id,
            run_id=run_id,
            created_by_tool=created_by_tool,
            kind=kind,
        )

    def save_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str | None,
        room_id: str | None = None,
        thread_id: str | None = None,
        run_id: str | None = None,
        created_by_tool: str | None = None,
        kind: str = "attachment",
    ) -> StoredAttachment:
        """Persist arbitrary bytes and return a stable attachment reference."""

        attachment_id = str(uuid4())
        suffix = Path(filename).suffix if filename else self._suffix_for_mime_type(mime_type)
        if not suffix:
            suffix = self._suffix_for_mime_type(mime_type)
        fallback_name = f"{attachment_id}{suffix}"
        file_name = filename or fallback_name
        ref = AttachmentRef(
            attachment_id=attachment_id,
            mime_type=mime_type,
            uri=f"/attachments/{attachment_id}",
            width=None,
            height=None,
            file_name=file_name,
        )
        resolved_room_id = self._resolve_room_id(room_id)
        resolved_thread_id = self._resolve_thread_id(thread_id)
        resolved_run_id = run_id if run_id is not None else self._run_id_var.get()
        storage_object = self._storage_backend.save_attachment(
            descriptor=StorageObjectDescriptor(
                attachment_id=attachment_id,
                thread_id=resolved_thread_id,
                run_id=resolved_run_id,
                file_name=file_name,
                mime_type=mime_type,
                kind=kind,
            ),
            content=content,
        )
        if self._asset_repository is not None:
            if resolved_room_id is None:
                msg = "Attachment persistence requires explicit room_id and thread_id."
                raise AttachmentContextError(msg)
            self._asset_repository.record_asset(
                asset_id=attachment_id,
                room_id=resolved_room_id,
                thread_id=resolved_thread_id,
                run_id=resolved_run_id,
                created_by_tool=created_by_tool,
                kind=kind,
                mime_type=mime_type,
                file_name=file_name,
                storage_path=storage_object.locator,
                sha256=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                width=None,
                height=None,
            )
        return StoredAttachment(
            ref=ref,
            path=storage_object.materialized_path,
            storage_locator=storage_object.locator,
        )

    def resolve(self, attachment_id: str) -> StoredAttachment | None:
        """Resolve stored attachment metadata for one attachment id."""

        if self._asset_repository is not None:
            persisted = self._asset_repository.get_asset(asset_id=attachment_id)
            if persisted is None:
                return None
            try:
                path = self._storage_backend.materialize_locator(
                    locator=persisted.storage_path,
                    attachment_id=attachment_id,
                    file_name=persisted.file_name,
                    mime_type=persisted.mime_type,
                )
            except FileNotFoundError:
                return None
            if not path.exists():
                return None
            mime_type = self._mime_type_for_suffix(path.suffix)
            ref = AttachmentRef(
                attachment_id=attachment_id,
                mime_type=persisted.mime_type or mime_type,
                uri=f"/attachments/{attachment_id}",
                width=persisted.width,
                height=persisted.height,
                file_name=persisted.file_name or path.name,
            )
            return StoredAttachment(
                ref=ref,
                path=path,
                storage_locator=persisted.storage_path,
            )
        path = self._storage_backend.find_local_path(attachment_id=attachment_id)
        if path is not None:
            mime_type = self._mime_type_for_suffix(path.suffix)
            ref = AttachmentRef(
                attachment_id=attachment_id,
                mime_type=mime_type,
                uri=f"/attachments/{attachment_id}",
                width=None,
                height=None,
                file_name=path.name,
            )
            return StoredAttachment(ref=ref, path=path, storage_locator=str(path))
        return None

    def _resolve_room_id(self, explicit_room_id: str | None) -> str | None:
        normalized_explicit = self._normalize_optional_room_id(explicit_room_id)
        if normalized_explicit is not None:
            return normalized_explicit
        return self._normalize_optional_room_id(self._room_id_var.get())

    def _resolve_thread_id(self, explicit_thread_id: str | None) -> str:
        normalized_explicit = self._normalize_optional_thread_id(explicit_thread_id)
        if normalized_explicit is not None:
            return normalized_explicit
        normalized_bound = self._normalize_optional_thread_id(self._thread_id_var.get())
        if normalized_bound is not None:
            return normalized_bound
        if self._asset_repository is None:
            return self._anonymous_thread_id
        msg = "Attachments require a real thread id; anonymous-thread fallback is not allowed."
        raise AttachmentContextError(msg)

    @staticmethod
    def _normalize_optional_room_id(room_id: str | None) -> str | None:
        if room_id is None:
            return None
        normalized = room_id.strip()
        return normalized or None

    @staticmethod
    def _normalize_optional_thread_id(thread_id: str | None) -> str | None:
        if thread_id is None:
            return None
        normalized = thread_id.strip()
        return normalized or None

    @classmethod
    def _normalize_thread_id(cls, thread_id: str) -> str:
        normalized = cls._normalize_optional_thread_id(thread_id)
        if normalized is None:
            msg = "Attachments require a non-empty thread id."
            raise AttachmentContextError(msg)
        return normalized

    @staticmethod
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

    @staticmethod
    def _mime_type_for_suffix(suffix: str) -> str:
        if suffix == ".png":
            return "image/png"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        if suffix == ".svg":
            return "image/svg+xml"
        return "application/octet-stream"
