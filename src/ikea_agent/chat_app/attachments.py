"""Attachment storage primitives for chat image uploads."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.shared.types import AttachmentRef


@dataclass(frozen=True, slots=True)
class StoredAttachment:
    """Concrete on-disk attachment metadata with the generated path."""

    ref: AttachmentRef
    path: Path


class AttachmentStore:
    """Simple local attachment store keyed by generated attachment IDs."""

    _thread_id_var: ContextVar[str]
    _run_id_var: ContextVar[str | None]

    def __init__(
        self,
        root_dir: Path,
        *,
        asset_repository: AssetRepository | None = None,
    ) -> None:
        """Create the store with a persistent root directory."""

        self._root_dir = root_dir
        self._asset_repository = asset_repository
        self._root_dir.mkdir(parents=True, exist_ok=True)
        self._thread_id_var = ContextVar("attachment_store_thread_id", default="anonymous-thread")
        self._run_id_var = ContextVar("attachment_store_run_id", default=None)

    @contextmanager
    def bind_context(self, *, thread_id: str, run_id: str | None) -> Iterator[None]:
        """Bind thread/run context for async request-local artifact persistence."""

        thread_token = self._thread_id_var.set(thread_id)
        run_token = self._run_id_var.set(run_id)
        try:
            yield
        finally:
            self._thread_id_var.reset(thread_token)
            self._run_id_var.reset(run_token)

    def save_image_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str | None,
        thread_id: str | None = None,
        run_id: str | None = None,
        created_by_tool: str | None = None,
        kind: str = "attachment",
    ) -> StoredAttachment:
        """Persist one image and return a stable attachment reference."""

        attachment_id = str(uuid4())
        suffix = self._suffix_for_mime_type(mime_type)
        fallback_name = f"{attachment_id}{suffix}"
        file_name = filename or fallback_name
        path = self._root_dir / fallback_name
        path.write_bytes(content)
        ref = AttachmentRef(
            attachment_id=attachment_id,
            mime_type=mime_type,
            uri=f"/attachments/{attachment_id}",
            width=None,
            height=None,
            file_name=file_name,
        )
        resolved_thread_id = thread_id or self._thread_id_var.get()
        resolved_run_id = run_id if run_id is not None else self._run_id_var.get()
        if self._asset_repository is not None:
            self._asset_repository.record_asset(
                asset_id=attachment_id,
                thread_id=resolved_thread_id,
                run_id=resolved_run_id,
                created_by_tool=created_by_tool,
                kind=kind,
                mime_type=mime_type,
                file_name=file_name,
                storage_path=str(path),
                sha256=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                width=None,
                height=None,
            )
        return StoredAttachment(ref=ref, path=path)

    def resolve(self, attachment_id: str) -> StoredAttachment | None:
        """Resolve stored attachment metadata for one attachment id."""

        for path in self._root_dir.glob(f"{attachment_id}.*"):
            mime_type = self._mime_type_for_suffix(path.suffix)
            ref = AttachmentRef(
                attachment_id=attachment_id,
                mime_type=mime_type,
                uri=f"/attachments/{attachment_id}",
                width=None,
                height=None,
                file_name=path.name,
            )
            return StoredAttachment(ref=ref, path=path)
        return None

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
