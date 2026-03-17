"""Generic callable aliases shared by eval helper modules."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

ReturnT = TypeVar("ReturnT")

AsyncService = Callable[..., Awaitable[ReturnT]]
SyncService = Callable[..., ReturnT]

__all__ = [
    "AsyncService",
    "SyncService",
]
