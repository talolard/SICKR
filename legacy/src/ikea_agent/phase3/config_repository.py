"""DuckDB-backed config repository for chat/runtime prompt and policy controls."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


@dataclass(frozen=True, slots=True)
class PromptTemplateConfigRow:
    """One active prompt template config row."""

    key: str
    version: str
    title: str
    template_text: str


@dataclass(frozen=True, slots=True)
class ExpansionPolicyConfigRow:
    """One expansion policy config row."""

    key: str
    title: str
    auto_mode_enabled: bool
    min_confidence: float
    min_constraint_signals: int


class ChatConfigRepository:
    """Read typed chat/runtime configuration entities from DuckDB."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def get_prompt_template(self, *, key: str, version: str) -> PromptTemplateConfigRow | None:
        """Return one active prompt template by key+version."""

        row = self._connection.execute(
            """
            SELECT key, version, title, template_text
            FROM app.system_prompt_template_config
            WHERE key = ?
              AND version = ?
              AND is_active = true
            LIMIT 1
            """,
            [key, version],
        ).fetchone()
        if row is None:
            return None
        return PromptTemplateConfigRow(
            key=str(row[0]),
            version=str(row[1]),
            title=str(row[2]),
            template_text=str(row[3]),
        )

    def get_active_expansion_policy(self, key: str = "default") -> ExpansionPolicyConfigRow | None:
        """Return one active expansion policy by key."""

        row = self._connection.execute(
            """
            SELECT key, title, auto_mode_enabled, min_confidence, min_constraint_signals
            FROM app.expansion_policy_config
            WHERE key = ?
              AND is_active = true
            LIMIT 1
            """,
            [key],
        ).fetchone()
        if row is None:
            return None
        return ExpansionPolicyConfigRow(
            key=str(row[0]),
            title=str(row[1]),
            auto_mode_enabled=bool(row[2]),
            min_confidence=float(row[3]),
            min_constraint_signals=int(row[4]),
        )
