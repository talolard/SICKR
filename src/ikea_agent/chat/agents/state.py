"""Shared AG-UI state models for agent-first runtime."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ikea_agent.shared.types import (
    AttachmentRef,
    BundleProposalToolResult,
    GroundedSearchProduct,
    KnownFactMemory,
    RoomType,
    SearchBatchToolResult,
)


class Room3DSnapshotCamera(BaseModel):
    """Camera metadata captured with one 3D perspective snapshot."""

    position_m: tuple[float, float, float]
    target_m: tuple[float, float, float]
    fov_deg: float


class Room3DSnapshotLighting(BaseModel):
    """Lighting emphasis metadata captured with one 3D snapshot."""

    light_fixture_ids: list[str] = Field(default_factory=list)
    emphasized_light_count: int = 0


class Room3DSnapshotContext(BaseModel):
    """UI-originated 3D snapshot context item shared into agent state."""

    snapshot_id: str
    attachment: AttachmentRef
    comment: str | None = None
    captured_at: str
    camera: Room3DSnapshotCamera
    lighting: Room3DSnapshotLighting


class CommonAgentState(BaseModel):
    """Common AG-UI state fields used by all first-class agents."""

    session_id: str | None = None
    branch_from_session_id: str | None = None
    project_id: str | None = None
    room_id: str | None = None
    room_title: str | None = None
    room_type: RoomType | None = None
    thread_id: str | None = None
    run_id: str | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)
    room_facts: list[KnownFactMemory] = Field(default_factory=list)
    project_facts: list[KnownFactMemory] = Field(default_factory=list)

    def remember_room_fact(self, fact: KnownFactMemory) -> None:
        """Upsert one persisted room fact into in-memory AG-UI state."""

        self.room_facts = _upsert_fact(self.room_facts, fact)

    def remember_project_fact(self, fact: KnownFactMemory) -> None:
        """Upsert one persisted project fact into in-memory AG-UI state."""

        self.project_facts = _upsert_fact(self.project_facts, fact)

    def set_room_profile(
        self,
        *,
        project_id: str | None,
        room_title: str | None,
        room_type: RoomType | None,
    ) -> None:
        """Update the active durable room identity snapshot in AG-UI state."""

        self.project_id = project_id
        self.room_title = room_title
        self.room_type = room_type


def _upsert_fact(current: list[KnownFactMemory], fact: KnownFactMemory) -> list[KnownFactMemory]:
    for index, existing in enumerate(current):
        if existing.signal_key == fact.signal_key and existing.value == fact.value:
            next_facts = list(current)
            next_facts[index] = fact
            return next_facts
    return [*current, fact]


class FloorPlanIntakeAgentState(CommonAgentState):
    """State for floor-plan intake agent runs."""


class SearchAgentState(CommonAgentState):
    """State for search agent runs."""

    room_3d_snapshots: list[Room3DSnapshotContext] = Field(default_factory=list)
    bundle_proposals: list[BundleProposalToolResult] = Field(default_factory=list)
    grounded_products: list[GroundedSearchProduct] = Field(default_factory=list)

    def append_bundle_proposal(self, proposal: BundleProposalToolResult) -> None:
        """Append one bundle proposal when it is not already present.

        Search bundle proposals can be replayed across AG-UI rerenders, so the
        state object owns deduplication by stable `bundle_id`.
        """

        if any(item.bundle_id == proposal.bundle_id for item in self.bundle_proposals):
            return
        self.bundle_proposals.append(proposal)

    def remember_search_batch(self, batch: SearchBatchToolResult) -> None:
        """Record product IDs returned by search so later bundle calls can stay grounded."""

        seen_product_ids = {item.product_id for item in self.grounded_products}
        for query in batch.queries:
            for result in query.results:
                if result.product_id in seen_product_ids:
                    continue
                self.grounded_products.append(
                    GroundedSearchProduct(
                        product_id=result.product_id,
                        product_name=result.product_name,
                        query_id=query.query_id,
                        semantic_query=query.semantic_query,
                    )
                )
                seen_product_ids.add(result.product_id)

    def grounded_product_ids(self) -> set[str]:
        """Return the grounded product ID set for quick bundle validation checks."""

        return {item.product_id for item in self.grounded_products}


class ImageAnalysisAgentState(CommonAgentState):
    """State for image-analysis agent runs."""
