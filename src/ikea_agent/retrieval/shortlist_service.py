"""Service wrapper for global shortlist persistence."""

from __future__ import annotations

from ikea_agent.config import get_settings
from ikea_agent.retrieval.repository import ShortlistRepository
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db import connect_db
from ikea_agent.shared.types import ShortlistState


class ShortlistService:
    """Provide add/remove/list operations for the global shortlist."""

    def __init__(self) -> None:
        settings = get_settings()
        self._connection = connect_db(settings.duckdb_path)
        ensure_runtime_schema(self._connection)
        self._repository = ShortlistRepository(self._connection)

    def add(self, canonical_product_key: str, note: str | None = None) -> None:
        """Add one product key to shortlist persistence."""

        self._repository.add(canonical_product_key, note)

    def remove(self, canonical_product_key: str) -> None:
        """Remove one product key from shortlist persistence."""

        self._repository.remove(canonical_product_key)

    def get_state(self) -> ShortlistState:
        """Return current shortlist state for display callers."""

        items = tuple(self._repository.list_items())
        return ShortlistState(items=items)
