"""Add durable conversation persistence tables.

Revision ID: 20260306_0002
Revises: 20260306_0001
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"

# revision identifiers, used by Alembic.
revision: str = "20260306_0002"
down_revision: str | Sequence[str] | None = "20260306_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    op.create_table(
        "threads",
        sa.Column("thread_id", sa.String(length=64), primary_key=True),
        sa.Column("owner_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_threads_owner_id", "threads", ["owner_id"], schema=APP_SCHEMA)
    op.create_index(
        "ix_threads_last_activity_at",
        "threads",
        ["last_activity_at"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("parent_run_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("user_prompt_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"], schema=APP_SCHEMA)
    op.create_index(
        "ix_agent_runs_parent_run_id",
        "agent_runs",
        ["parent_run_id"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "message_archives",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("archive_version", sa.Integer(), nullable=False),
        sa.Column("agui_input_messages_json", sa.Text(), nullable=True),
        sa.Column("pydantic_all_messages_json", sa.Text(), nullable=True),
        sa.Column("pydantic_new_messages_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        schema=APP_SCHEMA,
    )

    op.create_table(
        "assets",
        sa.Column("asset_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_tool", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_assets_thread_id", "assets", ["thread_id"], schema=APP_SCHEMA)
    op.create_index("ix_assets_run_id", "assets", ["run_id"], schema=APP_SCHEMA)
    op.create_index("ix_assets_sha256", "assets", ["sha256"], schema=APP_SCHEMA)

    op.create_table(
        "floor_plan_revisions",
        sa.Column("floor_plan_revision_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("scene_level", sa.String(length=32), nullable=False),
        sa.Column("scene_json", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("svg_asset_id", sa.String(length=64), nullable=True),
        sa.Column("png_asset_id", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_run_id", sa.String(length=64), nullable=True),
        sa.Column("confirmation_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["svg_asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        sa.ForeignKeyConstraint(["png_asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        sa.ForeignKeyConstraint(["confirmed_by_run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_floor_plan_revisions_thread_id",
        "floor_plan_revisions",
        ["thread_id"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "analysis_runs",
        sa.Column("analysis_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("input_asset_id", sa.String(length=64), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        sa.ForeignKeyConstraint(["input_asset_id"], [f"{APP_SCHEMA}.assets.asset_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_analysis_runs_thread_id", "analysis_runs", ["thread_id"], schema=APP_SCHEMA)
    op.create_index(
        "ix_analysis_runs_input_asset_id",
        "analysis_runs",
        ["input_asset_id"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "analysis_detections",
        sa.Column("analysis_detection_id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("bbox_x1_px", sa.Integer(), nullable=False),
        sa.Column("bbox_y1_px", sa.Integer(), nullable=False),
        sa.Column("bbox_x2_px", sa.Integer(), nullable=False),
        sa.Column("bbox_y2_px", sa.Integer(), nullable=False),
        sa.Column("bbox_x1_norm", sa.Float(), nullable=False),
        sa.Column("bbox_y1_norm", sa.Float(), nullable=False),
        sa.Column("bbox_x2_norm", sa.Float(), nullable=False),
        sa.Column("bbox_y2_norm", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], [f"{APP_SCHEMA}.analysis_runs.analysis_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_analysis_detections_analysis_id",
        "analysis_detections",
        ["analysis_id"],
        schema=APP_SCHEMA,
    )

    op.create_table(
        "search_runs",
        sa.Column("search_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("filters_json", sa.Text(), nullable=False),
        sa.Column("warning_json", sa.Text(), nullable=True),
        sa.Column("total_candidates", sa.Integer(), nullable=False),
        sa.Column("returned_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], [f"{APP_SCHEMA}.threads.thread_id"]),
        sa.ForeignKeyConstraint(["run_id"], [f"{APP_SCHEMA}.agent_runs.run_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index("ix_search_runs_thread_id", "search_runs", ["thread_id"], schema=APP_SCHEMA)

    op.create_table(
        "search_results",
        sa.Column("search_result_id", sa.String(length=64), primary_key=True),
        sa.Column("search_id", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=False),
        sa.Column("product_name", sa.String(length=512), nullable=False),
        sa.Column("product_type", sa.String(length=256), nullable=True),
        sa.Column("main_category", sa.String(length=256), nullable=True),
        sa.Column("sub_category", sa.String(length=256), nullable=True),
        sa.Column("width_cm", sa.Float(), nullable=True),
        sa.Column("depth_cm", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("price_eur", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["search_id"], [f"{APP_SCHEMA}.search_runs.search_id"]),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_search_results_search_id",
        "search_results",
        ["search_id"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_index("ix_search_results_search_id", table_name="search_results", schema=APP_SCHEMA)
    op.drop_table("search_results", schema=APP_SCHEMA)
    op.drop_index("ix_search_runs_thread_id", table_name="search_runs", schema=APP_SCHEMA)
    op.drop_table("search_runs", schema=APP_SCHEMA)
    op.drop_index(
        "ix_analysis_detections_analysis_id",
        table_name="analysis_detections",
        schema=APP_SCHEMA,
    )
    op.drop_table("analysis_detections", schema=APP_SCHEMA)
    op.drop_index("ix_analysis_runs_input_asset_id", table_name="analysis_runs", schema=APP_SCHEMA)
    op.drop_index("ix_analysis_runs_thread_id", table_name="analysis_runs", schema=APP_SCHEMA)
    op.drop_table("analysis_runs", schema=APP_SCHEMA)
    op.drop_index(
        "ix_floor_plan_revisions_thread_id",
        table_name="floor_plan_revisions",
        schema=APP_SCHEMA,
    )
    op.drop_table("floor_plan_revisions", schema=APP_SCHEMA)
    op.drop_index("ix_assets_sha256", table_name="assets", schema=APP_SCHEMA)
    op.drop_index("ix_assets_run_id", table_name="assets", schema=APP_SCHEMA)
    op.drop_index("ix_assets_thread_id", table_name="assets", schema=APP_SCHEMA)
    op.drop_table("assets", schema=APP_SCHEMA)
    op.drop_table("message_archives", schema=APP_SCHEMA)
    op.drop_index("ix_agent_runs_parent_run_id", table_name="agent_runs", schema=APP_SCHEMA)
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs", schema=APP_SCHEMA)
    op.drop_table("agent_runs", schema=APP_SCHEMA)
    op.drop_index("ix_threads_last_activity_at", table_name="threads", schema=APP_SCHEMA)
    op.drop_index("ix_threads_owner_id", table_name="threads", schema=APP_SCHEMA)
    op.drop_table("threads", schema=APP_SCHEMA)
