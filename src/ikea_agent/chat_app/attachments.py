"""Attachment storage primitives for chat image uploads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ikea_agent.shared.types import AttachmentRef


@dataclass(frozen=True, slots=True)
class StoredAttachment:
    """Concrete on-disk attachment metadata with the generated path."""

    ref: AttachmentRef
    path: Path


class AttachmentStore:
    """Simple local attachment store keyed by generated attachment IDs."""

    def __init__(self, root_dir: Path) -> None:
        """Create the store with a persistent root directory."""

        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def save_image_bytes(
        self,
        *,
        content: bytes,
        mime_type: str,
        filename: str | None,
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
        return ".bin"

    @staticmethod
    def _mime_type_for_suffix(suffix: str) -> str:
        if suffix == ".png":
            return "image/png"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "application/octet-stream"
