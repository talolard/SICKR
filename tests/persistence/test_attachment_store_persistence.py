from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.persistence.asset_repository import AssetRepository
from ikea_agent.persistence.models import AssetRecord, ensure_persistence_schema


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "attachment_store_test.sqlite")
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_save_image_bytes_persists_asset_metadata_with_context(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    store = AttachmentStore(
        tmp_path / "artifacts",
        asset_repository=AssetRepository(session_factory),
    )

    with store.bind_context(thread_id="thread-asset", run_id="run-missing"):
        stored = store.save_image_bytes(
            content=b"png-bytes",
            mime_type="image/png",
            filename="room.png",
            created_by_tool="upload",
            kind="user_upload",
        )

    with session_factory() as session:
        row = session.execute(
            select(
                AssetRecord.asset_id,
                AssetRecord.thread_id,
                AssetRecord.run_id,
                AssetRecord.kind,
                AssetRecord.mime_type,
                AssetRecord.file_name,
                AssetRecord.size_bytes,
                AssetRecord.storage_path,
            ).where(AssetRecord.asset_id == stored.ref.attachment_id)
        ).one()

    assert row.asset_id == stored.ref.attachment_id
    assert row.thread_id == "thread-asset"
    assert row.run_id is None
    assert row.kind == "user_upload"
    assert row.mime_type == "image/png"
    assert row.file_name == "room.png"
    assert row.size_bytes == len(b"png-bytes")
    assert Path(row.storage_path).exists()


def test_save_image_bytes_allows_explicit_thread_override(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    store = AttachmentStore(
        tmp_path / "artifacts",
        asset_repository=AssetRepository(session_factory),
    )

    with store.bind_context(thread_id="thread-context", run_id=None):
        stored = store.save_image_bytes(
            content=b"svg-bytes",
            mime_type="image/svg+xml",
            filename="plan.svg",
            thread_id="thread-explicit",
            kind="generated_preview",
        )

    with session_factory() as session:
        thread_id = session.execute(
            select(AssetRecord.thread_id).where(AssetRecord.asset_id == stored.ref.attachment_id)
        ).scalar_one()

    assert thread_id == "thread-explicit"


def test_save_image_bytes_repeated_writes_same_thread_are_sqlite_fk_safe(
    tmp_path: Path,
) -> None:
    session_factory = _session_factory(tmp_path)
    store = AttachmentStore(
        tmp_path / "artifacts",
        asset_repository=AssetRepository(session_factory),
    )

    with store.bind_context(thread_id="anonymous-thread", run_id=None):
        first = store.save_image_bytes(
            content=b"png-1",
            mime_type="image/png",
            filename="first.png",
            kind="user_upload",
        )
        second = store.save_image_bytes(
            content=b"png-2",
            mime_type="image/png",
            filename="second.png",
            kind="user_upload",
        )

    with session_factory() as session:
        thread_count = session.execute(
            select(AssetRecord.thread_id).where(AssetRecord.thread_id == "anonymous-thread")
        ).all()

    assert first.ref.attachment_id != second.ref.attachment_id
    assert len(thread_count) == 2
