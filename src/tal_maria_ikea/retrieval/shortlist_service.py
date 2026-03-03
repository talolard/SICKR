"""Service wrapper for global shortlist persistence."""

from __future__ import annotations

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.retrieval.repository import ShortlistRepository
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import ShortlistState


class ShortlistService:
    """Provide add/remove/list operations for the global shortlist."""

    def __init__(self) -> None:
        settings = get_settings()
        self._connection = connect_db(settings.duckdb_path)
        run_sql_file(self._connection, "sql/10_schema.sql")
        run_sql_file(self._connection, "sql/14_market_views.sql")
        self._repository = ShortlistRepository(self._connection)

    def add(self, canonical_product_key: str, note: str | None = None) -> None:
        """Add a product key to shortlist and keep latest timestamp."""

        self._repository.add(canonical_product_key, note)

    def remove(self, canonical_product_key: str) -> None:
        """Remove a shortlist entry by canonical product key."""

        self._repository.remove(canonical_product_key)

    def get_state(self) -> ShortlistState:
        """Return hydrated shortlist items in display order."""

        items = tuple(self._repository.list_items())
        return ShortlistState(items=items)
