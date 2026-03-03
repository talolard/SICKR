from __future__ import annotations

import pytest

from tal_maria_ikea.ingest.text_strategy import select_embedding_input_view


def test_select_embedding_input_view_v1() -> None:
    assert select_embedding_input_view("v1_baseline") == "app.embedding_input_v1_baseline"


def test_select_embedding_input_view_v2() -> None:
    assert (
        select_embedding_input_view("v2_metadata_first") == "app.embedding_input_v2_metadata_first"
    )


def test_select_embedding_input_view_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unsupported strategy version"):
        select_embedding_input_view("v3_unknown")  # type: ignore[arg-type]
