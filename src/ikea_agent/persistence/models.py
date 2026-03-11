"""SQLAlchemy models for durable conversation and artifact persistence.

The first migration stream keeps JSON payloads in text columns for maximum
dialect portability while the project is DuckDB-first and Postgres-ready.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Engine, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import text

APP_SCHEMA = "app"


class Base(DeclarativeBase):
    """Declarative base for persistence models."""


class ThreadRecord(Base):
    """Top-level thread metadata, including user-facing title."""

    __tablename__ = "threads"
    __table_args__ = (
        Index("ix_threads_owner_id", "owner_id"),
        Index("ix_threads_last_activity_at", "last_activity_at"),
        {"schema": APP_SCHEMA},
    )

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRunRecord(Base):
    """Lifecycle record for one agent run bound to a thread."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_thread_id", "thread_id"),
        Index("ix_agent_runs_parent_run_id", "parent_run_id"),
        {"schema": APP_SCHEMA},
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    parent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    user_prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageArchiveRecord(Base):
    """Raw AG-UI/PydanticAI message archive blobs for optional exact replay."""

    __tablename__ = "message_archives"
    __table_args__ = ({"schema": APP_SCHEMA},)

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        primary_key=True,
    )
    archive_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agui_input_messages_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    agui_event_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pydantic_all_messages_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pydantic_new_messages_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssetRecord(Base):
    """File-backed artifact metadata and associations."""

    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_thread_id", "thread_id"),
        Index("ix_assets_run_id", "run_id"),
        Index("ix_assets_sha256", "sha256"),
        {"schema": APP_SCHEMA},
    )

    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    created_by_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FloorPlanRevisionRecord(Base):
    """Durable floor-plan scene revision snapshots."""

    __tablename__ = "floor_plan_revisions"
    __table_args__ = (
        Index("ix_floor_plan_revisions_thread_id", "thread_id"),
        {"schema": APP_SCHEMA},
    )

    floor_plan_revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    scene_level: Mapped[str] = mapped_column(String(32), nullable=False)
    scene_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    svg_asset_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.assets.asset_id"),
        nullable=True,
    )
    png_asset_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.assets.asset_id"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    confirmation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Room3DAssetRecord(Base):
    """Thread-scoped OpenUSD asset bindings for room-scene workflows."""

    __tablename__ = "room_3d_assets"
    __table_args__ = (
        Index("ix_room_3d_assets_thread_id", "thread_id"),
        Index("ix_room_3d_assets_source_asset_id", "source_asset_id"),
        {"schema": APP_SCHEMA},
    )

    room_3d_asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    source_asset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.assets.asset_id"),
        nullable=False,
    )
    usd_format: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Room3DSnapshotRecord(Base):
    """Persisted 3D camera snapshots and linked metadata for one thread."""

    __tablename__ = "room_3d_snapshots"
    __table_args__ = (
        Index("ix_room_3d_snapshots_thread_id", "thread_id"),
        Index("ix_room_3d_snapshots_snapshot_asset_id", "snapshot_asset_id"),
        {"schema": APP_SCHEMA},
    )

    room_3d_snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    snapshot_asset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.assets.asset_id"),
        nullable=False,
    )
    room_3d_asset_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.room_3d_assets.room_3d_asset_id"),
        nullable=True,
    )
    camera_json: Mapped[str] = mapped_column(Text, nullable=False)
    lighting_json: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalysisRunRecord(Base):
    """Persistence row for image-analysis tool calls and outputs."""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_thread_id", "thread_id"),
        Index("ix_analysis_runs_input_asset_id", "input_asset_id"),
        {"schema": APP_SCHEMA},
    )

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_asset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.assets.asset_id"),
        nullable=False,
    )
    request_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalysisDetectionRecord(Base):
    """Normalized detection rows linked to one analysis run."""

    __tablename__ = "analysis_detections"
    __table_args__ = (
        Index("ix_analysis_detections_analysis_id", "analysis_id"),
        {"schema": APP_SCHEMA},
    )

    analysis_detection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.analysis_runs.analysis_id"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    bbox_x1_px: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y1_px: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x2_px: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y2_px: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x1_norm: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1_norm: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2_norm: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2_norm: Mapped[float] = mapped_column(Float, nullable=False)


class AnalysisFeedbackRecord(Base):
    """User feedback rows for analysis outcomes (confirm/reject/uncertain)."""

    __tablename__ = "analysis_feedback"
    __table_args__ = (
        Index("ix_analysis_feedback_analysis_id", "analysis_id"),
        Index("ix_analysis_feedback_thread_id", "thread_id"),
        {"schema": APP_SCHEMA},
    )

    analysis_feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.analysis_runs.analysis_id"),
        nullable=False,
    )
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    feedback_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    mask_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mask_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    query_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRunRecord(Base):
    """One persisted search invocation and aggregate metadata."""

    __tablename__ = "search_runs"
    __table_args__ = (
        Index("ix_search_runs_thread_id", "thread_id"),
        {"schema": APP_SCHEMA},
    )

    search_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.threads.thread_id"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.agent_runs.run_id"),
        nullable=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, nullable=False)
    warning_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False)
    returned_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchResultRecord(Base):
    """Persisted ranked result rows for one search invocation."""

    __tablename__ = "search_results"
    __table_args__ = (
        Index("ix_search_results_search_id", "search_id"),
        {"schema": APP_SCHEMA},
    )

    search_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{APP_SCHEMA}.search_runs.search_id"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    product_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    main_category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sub_category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    width_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)


def ensure_persistence_schema(engine: Engine) -> None:
    """Create persistence schema and tables when missing."""

    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
    Base.metadata.create_all(engine, checkfirst=True)
    _ensure_optional_columns(engine)


def _ensure_optional_columns(engine: Engine) -> None:
    """Backfill additive columns for local runtimes without migrations."""

    _ensure_column(
        engine,
        table_name="agent_runs",
        column_name="agent_name",
        column_sql="VARCHAR",
    )
    _ensure_column(
        engine,
        table_name="message_archives",
        column_name="agui_event_trace_json",
        column_sql="TEXT",
    )


def _ensure_column(
    engine: Engine,
    *,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    with engine.begin() as connection:
        column_exists = connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :table_schema
                  AND table_name = :table_name
                  AND column_name = :column_name
                """
            ),
            {
                "table_schema": APP_SCHEMA,
                "table_name": table_name,
                "column_name": column_name,
            },
        ).scalar_one_or_none()
        if column_exists is not None:
            return
        connection.execute(
            text(f"ALTER TABLE {APP_SCHEMA}.{table_name} ADD COLUMN {column_name} {column_sql}")
        )
