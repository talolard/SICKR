"""Embedding text strategy variants."""

from __future__ import annotations

from tal_maria_ikea.shared.types import EmbeddingStrategyVersion


def select_embedding_input_view(strategy_version: EmbeddingStrategyVersion) -> str:
    """Return the SQL view name for a strategy version."""

    if strategy_version == "v1_baseline":
        return "app.embedding_input_v1_baseline"

    if strategy_version == "v2_metadata_first":
        return "app.embedding_input_v2_metadata_first"

    message = f"Unsupported strategy version: {strategy_version}"
    raise ValueError(message)
