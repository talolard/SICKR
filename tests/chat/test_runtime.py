from __future__ import annotations

from ikea_agent.chat.runtime import build_google_embedding_settings


def test_google_embedding_settings_use_retrieval_query_task_type() -> None:
    settings = build_google_embedding_settings(dimensions=768)

    assert settings["dimensions"] == 768
    assert settings["google_task_type"] == "RETRIEVAL_QUERY"
