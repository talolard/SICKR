from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.persistence.revealed_preference_repository import RevealedPreferenceRepository
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
from ikea_agent.shared.types import RevealedPreferenceMemoryInput


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_duckdb_engine(str(tmp_path / "revealed_preference_repository_test.duckdb"))
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_upsert_preferences_persists_and_updates_thread_memory(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = RevealedPreferenceRepository(session_factory)

    repository.upsert_preferences(
        thread_id="thread-memory",
        run_id=None,
        preferences=[
            RevealedPreferenceMemoryInput(
                signal_key="household_member",
                kind="fact",
                value="toddler",
                summary="The household includes a toddler.",
                source_message_text="We have a toddler.",
            ),
            RevealedPreferenceMemoryInput(
                signal_key="safety_surface",
                kind="constraint",
                value="avoid_low_tables",
                summary="Avoid recommending low tables because the user said they sound risky.",
                source_message_text="A low table sounds risky with our toddler.",
            ),
        ],
    )
    listed = repository.upsert_preferences(
        thread_id="thread-memory",
        run_id=None,
        preferences=[
            RevealedPreferenceMemoryInput(
                signal_key="safety_surface",
                kind="constraint",
                value="avoid_low_tables",
                summary="Avoid recommending low tables because they sound risky with a toddler.",
                source_message_text="Placing something on a table that's low sounds risky.",
            )
        ],
    )

    assert len(listed) == 2
    assert listed[0].signal_key == "safety_surface"
    assert listed[0].summary.endswith("with a toddler.")
    assert listed[1].signal_key == "household_member"
