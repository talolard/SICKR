from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.models import AssetRecord, ThreadRecord, ensure_persistence_schema
from ikea_agent.persistence.ownership import ensure_default_dev_hierarchy
from ikea_agent.persistence.room_3d_repository import Room3DRepository


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "room_3d_repository_test.sqlite")
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _seed_source_assets(session_factory: sessionmaker[Session], *, tmp_path: Path) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
        hierarchy = ensure_default_dev_hierarchy(session, now=now)
        session.add(
            ThreadRecord(
                thread_id="thread-room3d",
                room_id=hierarchy.room_id,
                title=None,
                status="active",
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
        )
        session.flush()
        session.add(
            AssetRecord(
                asset_id="usd-source-asset",
                thread_id="thread-room3d",
                run_id=None,
                created_by_tool="test_seed",
                kind="room_3d_usd",
                mime_type="model/vnd.usd",
                file_name="room.usda",
                storage_path=str(tmp_path / "room.usda"),
                sha256="sha-room-usd",
                size_bytes=101,
                width=None,
                height=None,
                created_at=now,
            )
        )
        session.add(
            AssetRecord(
                asset_id="snapshot-png-asset",
                thread_id="thread-room3d",
                run_id=None,
                created_by_tool="test_seed",
                kind="room_3d_snapshot",
                mime_type="image/png",
                file_name="snapshot.png",
                storage_path=str(tmp_path / "snapshot.png"),
                sha256="sha-snapshot",
                size_bytes=202,
                width=640,
                height=480,
                created_at=now,
            )
        )
        session.commit()


def test_room_3d_repository_round_trip_assets_and_snapshots(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    _seed_source_assets(session_factory, tmp_path=tmp_path)
    repository = Room3DRepository(session_factory)

    stored_asset = repository.create_room_3d_asset(
        thread_id="thread-room3d",
        source_asset_id="usd-source-asset",
        usd_format="usda",
        metadata={"default_prim": "/Room", "mesh_count": 14},
        run_id=None,
    )

    stored_snapshot = repository.create_room_3d_snapshot(
        thread_id="thread-room3d",
        snapshot_asset_id="snapshot-png-asset",
        room_3d_asset_id=stored_asset.room_3d_asset_id,
        camera={"position_m": [1.0, 1.8, 2.2], "fov_deg": 55.0},
        lighting={"emphasized_light_count": 2, "light_fixture_ids": ["light-1", "light-2"]},
        comment="Need brighter desk area.",
        run_id=None,
    )

    listed_assets = repository.list_room_3d_assets(thread_id="thread-room3d")
    listed_snapshots = repository.list_room_3d_snapshots(thread_id="thread-room3d")
    loaded_asset = repository.get_room_3d_asset(room_3d_asset_id=stored_asset.room_3d_asset_id)
    loaded_snapshot = repository.get_room_3d_snapshot(
        room_3d_snapshot_id=stored_snapshot.room_3d_snapshot_id
    )

    assert stored_asset.usd_format == "usda"
    assert stored_asset.metadata["mesh_count"] == 14
    assert len(listed_assets) == 1
    assert loaded_asset is not None
    assert loaded_asset.source_asset_id == "usd-source-asset"

    assert stored_snapshot.snapshot_asset_id == "snapshot-png-asset"
    assert stored_snapshot.comment == "Need brighter desk area."
    assert len(listed_snapshots) == 1
    assert loaded_snapshot is not None
    assert loaded_snapshot.room_3d_asset_id == stored_asset.room_3d_asset_id
    assert loaded_snapshot.lighting["emphasized_light_count"] == 2
