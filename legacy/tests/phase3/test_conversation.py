from __future__ import annotations

from pathlib import Path

import duckdb
from ikea_agent.phase3.conversation import ConversationService
from ikea_agent.phase3.repository import (
    ConversationMessageEvent,
    ConversationThreadEvent,
    Phase3Repository,
)


def _setup_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))
    connection.execute(Path("sql/42_phase3_runtime.sql").read_text(encoding="utf-8"))


def test_conversation_service_appends_user_and_assistant_messages() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    repository = Phase3Repository(connection)
    repository.upsert_conversation_thread(
        ConversationThreadEvent(
            conversation_id="conv-1",
            request_id="req-1",
            user_ref=None,
            session_ref=None,
            title="Prompt compare",
            is_active=True,
        )
    )
    repository.insert_conversation_message(
        ConversationMessageEvent(
            message_id="msg-1",
            conversation_id="conv-1",
            role="assistant",
            content_text="Initial summary",
            prompt_run_id="run-1",
        )
    )

    response = ConversationService(repository).append_follow_up(
        conversation_id="conv-1",
        prompt_run_id="run-1",
        user_message="Why this item?",
    )

    assert response.strip() != ""
    messages = repository.list_conversation_messages("conv-1")
    assert len(messages) == 3
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"
