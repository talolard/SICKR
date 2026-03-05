"""DuckDB repository for Phase 3 telemetry and conversation persistence."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

import duckdb

from ikea_agent.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class SearchRequestEvent:
    """Persisted runtime metadata for one search request."""

    request_id: str
    query_text: str
    user_ref: str | None
    session_ref: str | None
    expansion_mode: str
    expansion_applied: bool
    filter_timing_mode: str
    rerank_enabled: bool
    request_source: str
    latency_ms: int | None


@dataclass(frozen=True, slots=True)
class SearchResultSnapshotRow:
    """One ranking-stage snapshot row for a request result item."""

    snapshot_id: str
    request_id: str
    ranking_stage: str
    rank_position: int
    canonical_product_key: str
    semantic_score: float | None
    rerank_score: float | None
    score_explanation: str | None


@dataclass(frozen=True, slots=True)
class PromptRunEvent:
    """One prompt execution event with prompt/rendering lineage."""

    prompt_run_id: str
    request_id: str
    variant_key: str
    variant_version: str
    rendered_system_prompt: str
    rendered_prompt_hash: str
    user_prompt: str
    context_payload_hash: str | None
    model_name: str
    status: str
    latency_ms: int | None
    error_message: str | None
    generation_config_json: str | None = None


@dataclass(frozen=True, slots=True)
class PromptTurnEvent:
    """One assistant turn linked to a prompt run and conversation thread."""

    turn_id: str
    prompt_run_id: str
    conversation_id: str
    summary_text: str | None
    response_json: dict[str, object]


@dataclass(frozen=True, slots=True)
class ConversationThreadEvent:
    """One thread-level conversation metadata upsert payload."""

    conversation_id: str
    request_id: str
    user_ref: str | None
    session_ref: str | None
    title: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class ConversationMessageEvent:
    """One conversation message payload."""

    message_id: str
    conversation_id: str
    role: str
    content_text: str
    prompt_run_id: str | None


@dataclass(frozen=True, slots=True)
class ConversationThreadRow:
    """Read model for one conversation thread listing row."""

    conversation_id: str
    request_id: str
    title: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class ConversationMessageRow:
    """Read model for one conversation message row."""

    message_id: str
    conversation_id: str
    role: str
    content_text: str
    prompt_run_id: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class TurnRatingEvent:
    """One turn-level feedback payload."""

    turn_rating_id: str
    turn_id: str
    request_id: str
    prompt_run_id: str
    thumb: str
    reason_tags: tuple[str, ...]
    note: str | None
    user_ref: str | None
    session_ref: str | None


@dataclass(frozen=True, slots=True)
class ItemRatingEvent:
    """One item-level feedback payload."""

    item_rating_id: str
    turn_id: str
    request_id: str
    prompt_run_id: str
    canonical_product_key: str
    thumb: str
    reason_tags: tuple[str, ...]
    note: str | None
    user_ref: str | None
    session_ref: str | None


@dataclass(frozen=True, slots=True)
class ResultDiffRow:
    """Read model for one before/after rerank delta row."""

    canonical_product_key: str
    product_name: str | None
    description_text: str | None
    rank_before: int
    rank_after: int
    semantic_score: float | None
    rerank_score: float | None
    rank_delta: int


@dataclass(frozen=True, slots=True)
class QueryCacheRow:
    """Read model for one cached query->request mapping row."""

    query_signature_hash: str
    request_id: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class SummaryCacheRow:
    """Read model for one cached summary payload row."""

    summary_cache_key: str
    summary_json: str
    expires_at: str


class Phase3Repository:
    """Persistence operations for Phase 3 event and conversation tables."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def insert_search_request(self, event: SearchRequestEvent) -> None:
        """Insert one search request runtime row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.search_request_v2 (
                request_id,
                query_text,
                user_ref,
                session_ref,
                expansion_mode,
                expansion_applied,
                filter_timing_mode,
                rerank_enabled,
                request_source,
                latency_ms,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                event.request_id,
                event.query_text,
                event.user_ref,
                event.session_ref,
                event.expansion_mode,
                event.expansion_applied,
                event.filter_timing_mode,
                event.rerank_enabled,
                event.request_source,
                event.latency_ms,
            ],
        )

    def insert_expansion_event(
        self,
        *,
        expansion_event_id: str,
        request_id: str,
        prompt_template_key: str | None,
        prompt_template_version: str | None,
        expanded_query_text: str | None,
        extracted_filters: dict[str, object] | None,
        confidence: float | None,
        heuristic_reason: str | None,
        applied: bool,
    ) -> None:
        """Insert one expansion decision row."""

        filters_json = (
            None if extracted_filters is None else json.dumps(extracted_filters, sort_keys=True)
        )
        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.search_expansion_event (
                expansion_event_id,
                request_id,
                prompt_template_key,
                prompt_template_version,
                expanded_query_text,
                extracted_filters_json,
                confidence,
                heuristic_reason,
                applied,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                expansion_event_id,
                request_id,
                prompt_template_key,
                prompt_template_version,
                expanded_query_text,
                filters_json,
                confidence,
                heuristic_reason,
                applied,
            ],
        )

    def insert_result_snapshots(self, rows: Sequence[SearchResultSnapshotRow]) -> None:
        """Insert multiple result ranking snapshot rows."""

        if not rows:
            return
        self._connection.executemany(
            """
            INSERT OR REPLACE INTO app.search_result_snapshot (
                snapshot_id,
                request_id,
                ranking_stage,
                rank_position,
                canonical_product_key,
                semantic_score,
                rerank_score,
                score_explanation,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                (
                    row.snapshot_id,
                    row.request_id,
                    row.ranking_stage,
                    row.rank_position,
                    row.canonical_product_key,
                    row.semantic_score,
                    row.rerank_score,
                    row.score_explanation,
                )
                for row in rows
            ],
        )

    def get_query_cache(
        self, *, query_signature_hash: str, cache_config_hash: str
    ) -> QueryCacheRow | None:
        """Return unexpired cached request mapping for one query signature."""

        row = self._connection.execute(
            """
            SELECT query_signature_hash, request_id, expires_at
            FROM app.search_query_cache
            WHERE query_signature_hash = ?
              AND cache_config_hash = ?
              AND expires_at > now()
            LIMIT 1
            """,
            [query_signature_hash, cache_config_hash],
        ).fetchone()
        if row is None:
            return None
        return QueryCacheRow(
            query_signature_hash=str(row[0]),
            request_id=str(row[1]),
            expires_at=str(row[2]),
        )

    def upsert_query_cache(
        self,
        *,
        query_signature_hash: str,
        request_id: str,
        query_text: str,
        filters_json: str,
        cache_config_hash: str,
        ttl_hours: int,
    ) -> None:
        """Insert or update one query cache row with expiration."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.search_query_cache (
                query_signature_hash,
                request_id,
                query_text,
                filters_json,
                cache_config_hash,
                expires_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, now() + (? * INTERVAL '1 hour'), now())
            """,
            [
                query_signature_hash,
                request_id,
                query_text,
                filters_json,
                cache_config_hash,
                ttl_hours,
            ],
        )

    def get_summary_cache(
        self, *, summary_cache_key: str, summary_config_hash: str
    ) -> SummaryCacheRow | None:
        """Return unexpired cached summary for one summary cache key."""

        row = self._connection.execute(
            """
            SELECT summary_cache_key, summary_json, expires_at
            FROM app.search_summary_cache
            WHERE summary_cache_key = ?
              AND summary_config_hash = ?
              AND expires_at > now()
            LIMIT 1
            """,
            [summary_cache_key, summary_config_hash],
        ).fetchone()
        if row is None:
            return None
        return SummaryCacheRow(
            summary_cache_key=str(row[0]),
            summary_json=str(row[1]),
            expires_at=str(row[2]),
        )

    def upsert_summary_cache(
        self,
        *,
        summary_cache_key: str,
        request_id: str,
        query_signature_hash: str,
        resultset_hash: str,
        summary_config_hash: str,
        summary_json: str,
        ttl_hours: int,
    ) -> None:
        """Insert or update one summary cache row with expiration."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.search_summary_cache (
                summary_cache_key,
                request_id,
                query_signature_hash,
                resultset_hash,
                summary_config_hash,
                summary_json,
                expires_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, now() + (? * INTERVAL '1 hour'), now())
            """,
            [
                summary_cache_key,
                request_id,
                query_signature_hash,
                resultset_hash,
                summary_config_hash,
                summary_json,
                ttl_hours,
            ],
        )

    def list_results_for_request(
        self, request_id: str, ranking_stage: str = "after_rerank"
    ) -> list[RetrievalResult]:
        """Hydrate ordered product results from persisted snapshot rows."""

        rows = self._connection.execute(
            """
            SELECT
                snapshot.canonical_product_key,
                coalesce(product.product_name, snapshot.canonical_product_key),
                product.product_type,
                product.description_text,
                NULL AS embedding_text,
                product.main_category,
                product.sub_category,
                product.dimensions_text,
                product.width_cm,
                product.depth_cm,
                product.height_cm,
                product.price_eur,
                product.url,
                snapshot.semantic_score,
                snapshot.score_explanation
            FROM app.search_result_snapshot AS snapshot
            LEFT JOIN app.products_canonical AS product
              ON product.canonical_product_key = snapshot.canonical_product_key
             AND product.country = 'Germany'
            WHERE snapshot.request_id = ?
              AND snapshot.ranking_stage = ?
            ORDER BY snapshot.rank_position ASC, snapshot.canonical_product_key ASC
            """,
            [request_id, ranking_stage],
        ).fetchall()

        results: list[RetrievalResult] = []
        for row in rows:
            semantic_score = _float_or_none(row[13]) or 0.0
            score_explanation = (
                _str_or_none(row[14]) or f"semantic cosine score {semantic_score:.3f}"
            )
            results.append(
                RetrievalResult(
                    canonical_product_key=str(row[0]),
                    product_name=str(row[1]),
                    product_type=_str_or_none(row[2]),
                    description_text=_str_or_none(row[3]),
                    embedding_text=_str_or_none(row[4]),
                    main_category=_str_or_none(row[5]),
                    sub_category=_str_or_none(row[6]),
                    dimensions_text=_str_or_none(row[7]),
                    width_cm=_float_or_none(row[8]),
                    depth_cm=_float_or_none(row[9]),
                    height_cm=_float_or_none(row[10]),
                    price_eur=_float_or_none(row[11]),
                    url=_str_or_none(row[12]),
                    semantic_score=semantic_score,
                    filter_pass_reasons=("structured_filters_passed",),
                    rank_explanation=score_explanation,
                )
            )
        return results

    def insert_prompt_run(self, event: PromptRunEvent) -> None:
        """Insert one prompt execution metadata row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.prompt_run (
                prompt_run_id,
                request_id,
                variant_key,
                variant_version,
                rendered_system_prompt,
                rendered_prompt_hash,
                user_prompt,
                context_payload_hash,
                model_name,
                status,
                latency_ms,
                error_message,
                generation_config_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                event.prompt_run_id,
                event.request_id,
                event.variant_key,
                event.variant_version,
                event.rendered_system_prompt,
                event.rendered_prompt_hash,
                event.user_prompt,
                event.context_payload_hash,
                event.model_name,
                event.status,
                event.latency_ms,
                event.error_message,
                event.generation_config_json,
            ],
        )

    def insert_prompt_turn(self, event: PromptTurnEvent) -> None:
        """Insert one assistant turn event."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.prompt_response_turn (
                turn_id,
                prompt_run_id,
                conversation_id,
                summary_text,
                response_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, now())
            """,
            [
                event.turn_id,
                event.prompt_run_id,
                event.conversation_id,
                event.summary_text,
                json.dumps(event.response_json, sort_keys=True),
            ],
        )

    def upsert_conversation_thread(self, event: ConversationThreadEvent) -> None:
        """Create or replace one conversation thread metadata row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.conversation_thread (
                conversation_id,
                request_id,
                user_ref,
                session_ref,
                title,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, now(), now())
            """,
            [
                event.conversation_id,
                event.request_id,
                event.user_ref,
                event.session_ref,
                event.title,
                event.is_active,
            ],
        )

    def insert_conversation_message(self, event: ConversationMessageEvent) -> None:
        """Insert one thread message row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.conversation_message (
                message_id,
                conversation_id,
                role,
                content_text,
                prompt_run_id,
                created_at
            ) VALUES (?, ?, ?, ?, ?, now())
            """,
            [
                event.message_id,
                event.conversation_id,
                event.role,
                event.content_text,
                event.prompt_run_id,
            ],
        )

    def insert_turn_rating(self, event: TurnRatingEvent) -> None:
        """Insert one turn-level feedback row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.feedback_turn_rating (
                turn_rating_id,
                turn_id,
                request_id,
                prompt_run_id,
                thumb,
                reason_tags_json,
                note,
                user_ref,
                session_ref,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                event.turn_rating_id,
                event.turn_id,
                event.request_id,
                event.prompt_run_id,
                event.thumb,
                json.dumps(event.reason_tags),
                event.note,
                event.user_ref,
                event.session_ref,
            ],
        )

    def insert_item_rating(self, event: ItemRatingEvent) -> None:
        """Insert one item-level feedback row."""

        self._connection.execute(
            """
            INSERT OR REPLACE INTO app.feedback_item_rating (
                item_rating_id,
                turn_id,
                request_id,
                prompt_run_id,
                canonical_product_key,
                thumb,
                reason_tags_json,
                note,
                user_ref,
                session_ref,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
            """,
            [
                event.item_rating_id,
                event.turn_id,
                event.request_id,
                event.prompt_run_id,
                event.canonical_product_key,
                event.thumb,
                json.dumps(event.reason_tags),
                event.note,
                event.user_ref,
                event.session_ref,
            ],
        )

    def list_result_diff(self, request_id: str) -> tuple[ResultDiffRow, ...]:
        """Return before/after ranking deltas for one request ID."""

        rows = self._connection.execute(
            """
            SELECT
                diff.canonical_product_key,
                product.product_name,
                product.description_text,
                diff.rank_before,
                diff.rank_after,
                diff.semantic_score,
                diff.rerank_score,
                diff.rank_delta
            FROM app.search_result_diff AS diff
            LEFT JOIN app.products_canonical AS product
              ON product.canonical_product_key = diff.canonical_product_key
             AND product.country = 'Germany'
            WHERE diff.request_id = ?
            ORDER BY diff.rank_after ASC, diff.canonical_product_key ASC
            """,
            [request_id],
        ).fetchall()

        return tuple(
            ResultDiffRow(
                canonical_product_key=str(row[0]),
                product_name=_str_or_none(row[1]),
                description_text=_str_or_none(row[2]),
                rank_before=int(row[3]),
                rank_after=int(row[4]),
                semantic_score=_float_or_none(row[5]),
                rerank_score=_float_or_none(row[6]),
                rank_delta=int(row[7]),
            )
            for row in rows
        )

    def list_result_keys_for_request(self, request_id: str, limit: int = 10) -> tuple[str, ...]:
        """Return top product keys from reranked snapshot rows for one request."""

        rows = self._connection.execute(
            """
            SELECT canonical_product_key
            FROM app.search_result_snapshot
            WHERE request_id = ?
              AND ranking_stage = 'after_rerank'
            ORDER BY rank_position ASC, canonical_product_key ASC
            LIMIT ?
            """,
            [request_id, limit],
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def list_conversation_threads(self, limit: int = 50) -> tuple[ConversationThreadRow, ...]:
        """Return recent active conversation threads for sidebar navigation."""

        rows = self._connection.execute(
            """
            SELECT conversation_id, request_id, title, updated_at
            FROM app.conversation_thread
            WHERE is_active = true
            ORDER BY updated_at DESC, conversation_id ASC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return tuple(
            ConversationThreadRow(
                conversation_id=str(row[0]),
                request_id=str(row[1]),
                title=_str_or_none(row[2]),
                updated_at=str(row[3]),
            )
            for row in rows
        )

    def list_conversation_messages(
        self, conversation_id: str, limit: int = 200
    ) -> tuple[ConversationMessageRow, ...]:
        """Return ordered messages for one conversation thread."""

        rows = self._connection.execute(
            """
            SELECT message_id, conversation_id, role, content_text, prompt_run_id, created_at
            FROM app.conversation_message
            WHERE conversation_id = ?
            ORDER BY created_at ASC, message_id ASC
            LIMIT ?
            """,
            [conversation_id, limit],
        ).fetchall()
        return tuple(
            ConversationMessageRow(
                message_id=str(row[0]),
                conversation_id=str(row[1]),
                role=str(row[2]),
                content_text=str(row[3]),
                prompt_run_id=_str_or_none(row[4]),
                created_at=str(row[5]),
            )
            for row in rows
        )

    def touch_conversation_thread(self, conversation_id: str) -> None:
        """Update thread timestamp after message append."""

        self._connection.execute(
            "UPDATE app.conversation_thread SET updated_at = now() WHERE conversation_id = ?",
            [conversation_id],
        )

    def latest_turn_id_for_prompt_run(self, prompt_run_id: str) -> str | None:
        """Return latest assistant turn ID for one prompt run."""

        row = self._connection.execute(
            """
            SELECT turn_id
            FROM app.prompt_response_turn
            WHERE prompt_run_id = ?
            ORDER BY created_at DESC, turn_id DESC
            LIMIT 1
            """,
            [prompt_run_id],
        ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def summarize_turn_feedback(self) -> tuple[tuple[str, int], ...]:
        """Return aggregate turn feedback counts grouped by thumb."""

        rows = self._connection.execute(
            """
            SELECT thumb, COUNT(*) AS feedback_count
            FROM app.feedback_turn_rating
            GROUP BY thumb
            ORDER BY thumb ASC
            """
        ).fetchall()
        return tuple((str(row[0]), int(row[1])) for row in rows)

    def summarize_item_feedback(self) -> tuple[tuple[str, int], ...]:
        """Return aggregate item feedback counts grouped by thumb."""

        rows = self._connection.execute(
            """
            SELECT thumb, COUNT(*) AS feedback_count
            FROM app.feedback_item_rating
            GROUP BY thumb
            ORDER BY thumb ASC
            """
        ).fetchall()
        return tuple((str(row[0]), int(row[1])) for row in rows)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
