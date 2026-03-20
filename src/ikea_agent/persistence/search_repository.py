"""Persistence helpers for semantic-search run snapshots and ranked results."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    BundleProposalRecord,
    SearchResultRecord,
    SearchRunRecord,
)
from ikea_agent.persistence.ownership import require_thread_record
from ikea_agent.persistence.repository_helpers import (
    resolve_existing_run_id,
    touch_thread_activity,
)
from ikea_agent.shared.types import (
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    RetrievalFilters,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)


class SearchRepository:
    """Repository for storing room-owned search snapshots with thread provenance."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_search_run(
        self,
        *,
        room_id: str,
        thread_id: str,
        run_id: str | None,
        query_text: str,
        filters: RetrievalFilters | None,
        warning: SearchResultDiversityWarning | None,
        total_candidates: int,
        results: list[ShortRetrievalResult],
    ) -> str:
        """Persist one semantic-search run and its ranked result rows."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            require_thread_record(session, room_id=room_id, thread_id=thread_id)

            persisted_run_id = resolve_existing_run_id(session, run_id=run_id)
            search_id = f"search-{uuid4().hex[:24]}"
            session.add(
                SearchRunRecord(
                    search_id=search_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    query_text=query_text,
                    filters_json=json.dumps(
                        asdict(filters) if filters is not None else {},
                        sort_keys=True,
                    ),
                    warning_json=(
                        json.dumps(asdict(warning), sort_keys=True) if warning is not None else None
                    ),
                    total_candidates=total_candidates,
                    returned_count=len(results),
                    created_at=now,
                )
            )
            session.flush()

            for index, item in enumerate(results):
                session.add(
                    SearchResultRecord(
                        search_result_id=f"sres-{search_id[-20:]}-{index + 1:04d}",
                        search_id=search_id,
                        rank=index + 1,
                        product_id=item.product_id,
                        product_name=item.product_name,
                        product_type=item.product_type,
                        main_category=item.main_category,
                        sub_category=item.sub_category,
                        width_cm=item.width_cm,
                        depth_cm=item.depth_cm,
                        height_cm=item.height_cm,
                        price_eur=item.price_eur,
                    )
                )
            touch_thread_activity(session, thread_id=thread_id, now=now)
            session.commit()
            return search_id

    def record_bundle_proposal(
        self,
        *,
        room_id: str,
        thread_id: str,
        run_id: str | None,
        proposal: BundleProposalToolResult,
    ) -> str:
        """Persist one hydrated bundle proposal for later room reloads."""

        created_at = datetime.fromisoformat(proposal.created_at)
        with self._session_factory() as session:
            require_thread_record(session, room_id=room_id, thread_id=thread_id)

            persisted_run_id = resolve_existing_run_id(session, run_id=run_id)
            session.merge(
                BundleProposalRecord(
                    bundle_id=proposal.bundle_id,
                    room_id=room_id,
                    thread_id=thread_id,
                    run_id=persisted_run_id,
                    title=proposal.title,
                    notes=proposal.notes,
                    budget_cap_eur=proposal.budget_cap_eur,
                    bundle_total_eur=proposal.bundle_total_eur,
                    items_json=json.dumps(
                        [item.model_dump(mode="json") for item in proposal.items],
                        sort_keys=True,
                    ),
                    validations_json=json.dumps(
                        [item.model_dump(mode="json") for item in proposal.validations],
                        sort_keys=True,
                    ),
                    created_at=created_at,
                )
            )
            touch_thread_activity(session, thread_id=thread_id, now=created_at)
            session.commit()
        return proposal.bundle_id

    def list_bundle_proposals(self, *, room_id: str) -> list[BundleProposalToolResult]:
        """Return bundle proposals for a room ordered newest-first."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    BundleProposalRecord.bundle_id,
                    BundleProposalRecord.run_id,
                    BundleProposalRecord.title,
                    BundleProposalRecord.notes,
                    BundleProposalRecord.budget_cap_eur,
                    BundleProposalRecord.bundle_total_eur,
                    BundleProposalRecord.items_json,
                    BundleProposalRecord.validations_json,
                    cast(BundleProposalRecord.created_at, String),
                )
                .where(BundleProposalRecord.room_id == room_id)
                .order_by(BundleProposalRecord.created_at.desc())
            ).all()
        return [
            BundleProposalToolResult(
                bundle_id=str(item.bundle_id),
                title=str(item.title),
                notes=str(item.notes) if item.notes is not None else None,
                budget_cap_eur=(
                    float(item.budget_cap_eur) if item.budget_cap_eur is not None else None
                ),
                items=_load_bundle_items(item.items_json),
                bundle_total_eur=(
                    float(item.bundle_total_eur) if item.bundle_total_eur is not None else None
                ),
                validations=_load_bundle_validations(item.validations_json),
                created_at=str(item.created_at),
                run_id=str(item.run_id) if item.run_id is not None else None,
            )
            for item in rows
        ]


def _load_bundle_items(raw_items: object) -> list[BundleProposalLineItem]:
    if not isinstance(raw_items, str):
        return []
    loaded = json.loads(raw_items)
    if not isinstance(loaded, list):
        return []
    return [BundleProposalLineItem.model_validate(item) for item in loaded]


def _load_bundle_validations(raw_validations: object) -> list[BundleValidationResult]:
    if not isinstance(raw_validations, str):
        return []
    loaded = json.loads(raw_validations)
    if not isinstance(loaded, list):
        return []
    return [BundleValidationResult.model_validate(item) for item in loaded]
