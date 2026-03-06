"""Persistence helpers for semantic-search run snapshots and ranked results."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    AgentRunRecord,
    SearchResultRecord,
    SearchRunRecord,
    ThreadRecord,
)
from ikea_agent.shared.types import (
    RetrievalFilters,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)


class SearchRepository:
    """Repository for storing thread-scoped search snapshots and result rows."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_search_run(
        self,
        *,
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
            self._ensure_thread(session=session, thread_id=thread_id, now=now)
            session.flush()

            persisted_run_id = self._resolve_existing_run_id(session=session, run_id=run_id)
            search_id = f"search-{uuid4().hex[:24]}"
            session.add(
                SearchRunRecord(
                    search_id=search_id,
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
            session.commit()
            return search_id

    def list_search_runs(self, *, thread_id: str) -> list[str]:
        """Return search ids for a thread ordered newest-first."""

        with self._session_factory() as session:
            rows = session.execute(
                select(SearchRunRecord.search_id)
                .where(SearchRunRecord.thread_id == thread_id)
                .order_by(SearchRunRecord.created_at.desc())
            ).scalars()
            return [str(item) for item in rows]

    @staticmethod
    def _ensure_thread(*, session: Session, thread_id: str, now: datetime) -> None:
        existing_thread_id = session.execute(
            select(ThreadRecord.thread_id).where(ThreadRecord.thread_id == thread_id)
        ).scalar_one_or_none()
        if existing_thread_id is not None:
            return
        session.add(
            ThreadRecord(
                thread_id=thread_id,
                owner_id=None,
                title=None,
                status="active",
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
        )

    @staticmethod
    def _resolve_existing_run_id(*, session: Session, run_id: str | None) -> str | None:
        if run_id is None:
            return None
        return session.execute(
            select(AgentRunRecord.run_id).where(AgentRunRecord.run_id == run_id)
        ).scalar_one_or_none()
