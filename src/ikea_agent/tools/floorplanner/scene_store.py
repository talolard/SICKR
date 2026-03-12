"""Thread-scoped in-memory scene store for floor-plan workflows."""

from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.tools.floorplanner.models import FloorPlanScene, clone_scene


@dataclass(slots=True)
class SceneSnapshot:
    """Stored scene snapshot with monotonically increasing revision."""

    revision: int
    scene: FloorPlanScene


class FloorPlanSceneStore:
    """In-memory state keyed by session id for iterative placement updates."""

    def __init__(self) -> None:
        self._by_session: dict[str, SceneSnapshot] = {}

    def get(self, session_id: str | None) -> SceneSnapshot | None:
        """Get snapshot for one session when available."""

        if session_id is None:
            return None
        snapshot = self._by_session.get(session_id)
        if snapshot is None:
            return None
        return SceneSnapshot(revision=snapshot.revision, scene=clone_scene(snapshot.scene))

    def set(self, session_id: str | None, scene: FloorPlanScene) -> SceneSnapshot:
        """Store a new snapshot and increment revision for the session."""

        key = session_id or "__anonymous__"
        current = self._by_session.get(key)
        revision = 1 if current is None else current.revision + 1
        return self.set_with_revision(session_id, scene, revision=revision)

    def set_with_revision(
        self,
        session_id: str | None,
        scene: FloorPlanScene,
        *,
        revision: int,
    ) -> SceneSnapshot:
        """Store a snapshot with an explicit revision number."""

        key = session_id or "__anonymous__"
        snapshot = SceneSnapshot(revision=revision, scene=clone_scene(scene))
        self._by_session[key] = snapshot
        return SceneSnapshot(revision=snapshot.revision, scene=clone_scene(snapshot.scene))
