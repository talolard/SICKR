"""Validation and lightweight inspection utilities for OpenUSD uploads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

try:
    from pxr import Usd as _Usd  # type: ignore[import-untyped]
except ImportError:
    _Usd = None

SUPPORTED_OPENUSD_EXTENSIONS: frozenset[str] = frozenset({".usda", ".usd", ".usdc", ".usdz"})


class OpenUsdValidationError(ValueError):
    """Raised when uploaded OpenUSD content is unsupported or invalid."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class OpenUsdInspection:
    """Lightweight inspection metadata extracted from a validated OpenUSD file."""

    usd_format: str
    metadata: dict[str, Any]


def inspect_openusd_bytes(*, content: bytes, filename: str) -> OpenUsdInspection:
    """Validate one OpenUSD payload and return typed inspection metadata."""

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_OPENUSD_EXTENSIONS:
        raise OpenUsdValidationError(
            code="unsupported_extension",
            message="Supported OpenUSD formats: .usda, .usd, .usdc, .usdz.",
        )
    if not content:
        raise OpenUsdValidationError(
            code="empty_payload", message="Uploaded OpenUSD file is empty."
        )

    with NamedTemporaryFile(suffix=extension, delete=True) as temp_file:
        temp_path = Path(temp_file.name)
        temp_path.write_bytes(content)
        return _inspect_openusd_file(path=temp_path)


def _inspect_openusd_file(*, path: Path) -> OpenUsdInspection:
    extension = path.suffix.lower().removeprefix(".")
    if _Usd is None:
        return _fallback_inspection(path=path, usd_format=extension)

    try:
        stage = cast("Any", _Usd).Stage.Open(str(path))
    except Exception:
        # Some local/dev payloads may still be useful to persist as placeholders
        # for later binding flows; keep strict text checks for USDA only.
        if extension == "usda":
            raise OpenUsdValidationError(
                code="invalid_openusd",
                message=(
                    "OpenUSD stage could not be opened. Check that the file is a valid USD asset."
                ),
            ) from None
        return _fallback_inspection(path=path, usd_format=extension)
    if stage is None:
        if extension == "usda":
            raise OpenUsdValidationError(
                code="invalid_openusd",
                message=(
                    "OpenUSD stage could not be opened. Check that the file is a valid USD asset."
                ),
            )
        return _fallback_inspection(path=path, usd_format=extension)

    default_prim = stage.GetDefaultPrim()
    prim_count = sum(1 for _ in stage.Traverse())
    metadata: dict[str, Any] = {
        "validation_backend": "pxr",
        "default_prim": default_prim.GetPath().pathString if default_prim.IsValid() else None,
        "prim_count": prim_count,
        "root_layer_identifier": stage.GetRootLayer().identifier,
    }
    return OpenUsdInspection(usd_format=extension, metadata=metadata)


def _fallback_inspection(*, path: Path, usd_format: str) -> OpenUsdInspection:
    content = path.read_bytes()
    if usd_format == "usda":
        text = content.decode("utf-8", errors="ignore")
        if "#usda" not in text and "def " not in text and "over " not in text:
            raise OpenUsdValidationError(
                code="invalid_openusd_text",
                message="USDA text did not contain recognizable USD markers.",
            )

    metadata: dict[str, Any] = {
        "validation_backend": "fallback",
        "byte_size": len(content),
    }
    return OpenUsdInspection(usd_format=usd_format, metadata=metadata)
