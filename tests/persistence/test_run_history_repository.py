from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    AgentRunRecord,
    MessageArchiveRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.run_history_repository import (
    RunHistoryRepository,
    ThreadRunHistoryEntry,
    extract_last_user_prompt,
)
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_duckdb_engine(str(tmp_path / "run_history_test.duckdb"))
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_extract_last_user_prompt_returns_latest_user_text() -> None:
    prompt = extract_last_user_prompt(
        [
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "   first  "},
            {"role": "user", "content": " second "},
        ]
    )
    assert prompt == "second"


def test_record_run_start_and_complete_persists_archive(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        thread_id="thread-a",
        run_id="run-a",
        parent_run_id=None,
        user_prompt_text="design room",
        agui_input_messages_json='[{"role":"user","content":"design room"}]',
    )
    repository.record_run_complete(
        run_id="run-a",
        pydantic_all_messages_json=b'[{"kind":"request"}]',
        pydantic_new_messages_json=b'[{"kind":"response"}]',
    )

    with session_factory() as session:
        run_status = session.execute(
            select(AgentRunRecord.status).where(AgentRunRecord.run_id == "run-a")
        ).scalar_one()
        archive_row = session.execute(
            select(
                MessageArchiveRecord.agui_input_messages_json,
                MessageArchiveRecord.pydantic_all_messages_json,
            ).where(MessageArchiveRecord.run_id == "run-a")
        ).one()

    assert run_status == "completed"
    assert archive_row.agui_input_messages_json is not None
    assert archive_row.pydantic_all_messages_json == '[{"kind":"request"}]'


def test_record_run_failed_sets_failed_status(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)
    repository.record_run_start(
        thread_id="thread-b",
        run_id="run-b",
        parent_run_id="run-root",
        user_prompt_text=None,
        agui_input_messages_json="[]",
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
        thread_id="thread-c",
        run_id="run-c-1",
        parent_run_id=None,
        user_prompt_text="first",
        agui_input_messages_json="[]",
    )
    repository.record_run_start(
        thread_id="thread-c",
        run_id="run-c-2",
        parent_run_id=None,
        user_prompt_text="second",
        agui_input_messages_json="[]",
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

    repository.record_run_complete(
        run_id="missing-run",
        pydantic_all_messages_json=b"[]",
        pydantic_new_messages_json=b"[]",
    )

    with session_factory() as session:
        archives = session.execute(select(MessageArchiveRecord.run_id)).scalars().all()

    assert archives == []


def test_list_thread_run_history_returns_ordered_archive_rows(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RunHistoryRepository(session_factory)

    repository.record_run_start(
        thread_id="thread-h",
        run_id="run-h-1",
        parent_run_id=None,
        user_prompt_text="first user prompt",
        agui_input_messages_json='[{"role":"user","content":"first user prompt"}]',
    )
    repository.record_run_complete(
        run_id="run-h-1",
        pydantic_all_messages_json=b'[{"kind":"request","text":"first"}]',
        pydantic_new_messages_json=b'[{"kind":"response","text":"ok"}]',
    )
    repository.record_run_start(
        thread_id="thread-h",
        run_id="run-h-2",
        parent_run_id="run-h-1",
        user_prompt_text="second user prompt",
        agui_input_messages_json='[{"role":"user","content":"second user prompt"}]',
    )

    history = repository.list_thread_run_history(thread_id="thread-h")

    assert history
    assert all(isinstance(entry, ThreadRunHistoryEntry) for entry in history)
    assert history[0].run_id == "run-h-1"
    assert history[0].pydantic_all_messages_json is not None
    assert history[1].run_id == "run-h-2"
    assert history[1].parent_run_id == "run-h-1"
