from __future__ import annotations

from pathlib import Path

from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.models import (
    AgentRunRecord,
    ThreadMessageSegmentRecord,
    ThreadRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.ownership import DEFAULT_DEV_ROOM_ID
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    extract_last_user_prompt,
)


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "run_history_test.sqlite")
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _message_batch(user_text: str, assistant_text: str) -> bytes:
    return ModelMessagesTypeAdapter.dump_json(
        [
            ModelRequest(parts=[UserPromptPart(content=user_text)], run_id="model-run"),
            ModelResponse(parts=[TextPart(content=assistant_text)], model_name="test-model"),
        ]
    )


def test_extract_last_user_prompt_returns_latest_user_text() -> None:
    prompt = extract_last_user_prompt(
        [
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "   first  "},
            {"role": "user", "content": " second "},
        ]
    )
    assert prompt == "second"


def test_record_run_start_and_complete_persists_run_lifecycle(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-a",
        run_id="run-a",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="design room",
    )
    repository.record_run_complete(run_id="run-a")

    with session_factory() as session:
        run_row = session.execute(
            select(AgentRunRecord.status, AgentRunRecord.agent_name).where(
                AgentRunRecord.run_id == "run-a"
            )
        ).one()

    assert run_row.status == "completed"
    assert run_row.agent_name == "search"


def test_record_run_complete_persists_canonical_message_segment(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-history",
        run_id="run-history-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="design room",
    )
    repository.record_run_complete(
        run_id="run-history-1",
        new_messages_json=_message_batch("hello", "hi there"),
    )

    with session_factory() as session:
        stored_segment = session.execute(
            select(
                ThreadMessageSegmentRecord.thread_id,
                ThreadMessageSegmentRecord.run_id,
                ThreadMessageSegmentRecord.sequence_no,
            ).where(ThreadMessageSegmentRecord.run_id == "run-history-1")
        ).one()

    assert stored_segment.thread_id == "thread-history"
    assert stored_segment.run_id == "run-history-1"
    assert stored_segment.sequence_no == 1


def test_load_message_history_returns_ordered_thread_history(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-history",
        run_id="run-history-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="first",
    )
    repository.record_run_complete(
        run_id="run-history-1",
        new_messages_json=_message_batch("hello", "hi there"),
    )
    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-history",
        run_id="run-history-2",
        agent_name="search",
        parent_run_id="run-history-1",
        user_prompt_text="second",
    )
    repository.record_run_complete(
        run_id="run-history-2",
        new_messages_json=_message_batch("what now?", "next step"),
    )

    history = repository.load_message_history(thread_id="thread-history")

    assert len(history) == 4
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[1], ModelResponse)
    assert isinstance(history[2], ModelRequest)
    assert isinstance(history[3], ModelResponse)
    first_request_part = history[0].parts[0]
    second_response_part = history[3].parts[0]
    assert isinstance(first_request_part, UserPromptPart)
    assert isinstance(second_response_part, TextPart)
    assert first_request_part.content == "hello"
    assert second_response_part.content == "next step"


def test_record_run_failed_sets_failed_status(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)
    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-b",
        run_id="run-b",
        agent_name="search",
        parent_run_id="run-root",
        user_prompt_text=None,
    )

    repository.record_run_failed(run_id="run-b", error_message="boom")

    with session_factory() as session:
        run_row = session.execute(
            select(
                AgentRunRecord.status,
                AgentRunRecord.error_message,
            ).where(AgentRunRecord.run_id == "run-b")
        ).one()

    assert run_row.status == "failed"
    assert run_row.error_message == "boom"


def test_record_run_start_is_fk_safe_for_existing_thread_with_child_runs(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-c",
        run_id="run-c-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="first",
    )
    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-c",
        run_id="run-c-2",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="second",
    )

    with session_factory() as session:
        run_ids = (
            session.execute(
                select(AgentRunRecord.run_id).where(AgentRunRecord.thread_id == "thread-c")
            )
            .scalars()
            .all()
        )

    assert set(run_ids) == {"run-c-1", "run-c-2"}


def test_record_run_complete_missing_run_is_noop(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_complete(run_id="missing-run")

    with session_factory() as session:
        run_ids = session.execute(select(AgentRunRecord.run_id)).scalars().all()

    assert run_ids == []


def test_record_run_start_creates_thread_row(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        room_id=DEFAULT_DEV_ROOM_ID,
        thread_id="thread-z",
        run_id="run-z-1",
        agent_name="search",
        parent_run_id=None,
        user_prompt_text="first user prompt",
    )

    with session_factory() as session:
        thread_row = session.execute(
            select(ThreadRecord.thread_id, ThreadRecord.room_id, ThreadRecord.status).where(
                ThreadRecord.thread_id == "thread-z"
            )
        ).one()

    assert thread_row.thread_id == "thread-z"
    assert thread_row.room_id == DEFAULT_DEV_ROOM_ID
    assert thread_row.status == "active"
