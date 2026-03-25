from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.context_fact_repository import ContextFactRepository
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.ownership import (
    DEFAULT_DEV_ROOM_ID,
    ensure_default_dev_hierarchy_for_session_factory,
)
from ikea_agent.shared.types import KnownFactMemoryInput


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "context_fact_repository_test.sqlite")
    ensure_persistence_schema(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    ensure_default_dev_hierarchy_for_session_factory(session_factory)
    return session_factory


def test_upsert_room_and_project_facts_persists_and_updates_context(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = ContextFactRepository(session_factory)
    room_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)

    repository.upsert_room_facts(
        room_id=DEFAULT_DEV_ROOM_ID,
        run_id=None,
        facts=[
            KnownFactMemoryInput(
                signal_key="household_member",
                kind="fact",
                value="toddler",
                summary="The household includes a toddler.",
                source_message_text="We have a toddler.",
            ),
            KnownFactMemoryInput(
                signal_key="safety_surface",
                kind="constraint",
                value="avoid_low_tables",
                summary="Avoid recommending low tables because the user said they sound risky.",
                source_message_text="A low table sounds risky with our toddler.",
            ),
        ],
    )
    listed_project_facts = repository.upsert_project_facts(
        project_id=room_context.room_identity.project_id,
        run_id=None,
        facts=[
            KnownFactMemoryInput(
                signal_key="wall_rules",
                kind="constraint",
                value="avoid_drilling",
                summary="Avoid drilling into the walls across the project.",
                source_message_text="The rental does not allow drilling.",
            )
        ],
    )
    listed_room_facts = repository.upsert_room_facts(
        room_id=DEFAULT_DEV_ROOM_ID,
        run_id=None,
        facts=[
            KnownFactMemoryInput(
                signal_key="safety_surface",
                kind="constraint",
                value="avoid_low_tables",
                summary="Avoid recommending low tables because they sound risky with a toddler.",
                source_message_text="Placing something on a table that's low sounds risky.",
            )
        ],
    )

    refreshed_context = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)

    assert len(listed_room_facts) == 2
    assert listed_room_facts[0].scope == "room"
    assert listed_room_facts[0].signal_key == "safety_surface"
    assert listed_room_facts[0].summary.endswith("with a toddler.")
    assert listed_room_facts[1].signal_key == "household_member"
    assert len(listed_project_facts) == 1
    assert listed_project_facts[0].scope == "project"
    assert listed_project_facts[0].value == "avoid_drilling"
    assert [item.value for item in refreshed_context.room_facts] == [
        "avoid_low_tables",
        "toddler",
    ]
    assert [item.value for item in refreshed_context.project_facts] == ["avoid_drilling"]


def test_room_identity_updates_persist_title_and_type(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = ContextFactRepository(session_factory)

    renamed = repository.rename_room(room_id=DEFAULT_DEV_ROOM_ID, title="Son's room")
    typed = repository.set_room_type(room_id=DEFAULT_DEV_ROOM_ID, room_type="bedroom")
    refreshed = repository.load_room_context(room_id=DEFAULT_DEV_ROOM_ID)

    assert renamed.title == "Son's room"
    assert typed.room_type == "bedroom"
    assert refreshed.room_identity.title == "Son's room"
    assert refreshed.room_identity.room_type == "bedroom"
