"""Repo-local Vulture keep rules for framework and compatibility false positives."""

from ikea_agent.chat.agents.index import AgentCatalogItem, AgentDescription
from ikea_agent.chat.agents.state import (
    Room3DSnapshotCamera,
    Room3DSnapshotContext,
    Room3DSnapshotLighting,
)
from ikea_agent.chat.runtime import GoogleEmbeddingSettings
from ikea_agent.chat_app.thread_api_models import (
    RecentTraceReportListResponse,
    TraceReportCreateResponse,
)
from ikea_agent.config import AppSettings
from ikea_agent.persistence.models import (
    MessageArchiveRecord,
    SearchResultRecord,
    ThreadRecord,
)
from ikea_agent.persistence.run_history_repository import RunHistoryRepository
from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.retrieval.schema import (
    product_embedding_neighbors,
    product_embeddings,
    products_canonical,
)
from ikea_agent.shared.alembic_duckdb import DuckDBImpl
from ikea_agent.shared.db import connect_db, run_sql_file
from ikea_agent.shared.types import (
    BundleProposalItemInput,
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    RetrievalResult,
    SearchQueryInput,
)
from ikea_agent.tools.floorplanner.models import (
    BaselineFloorPlanScene,
    DetailedFloorPlanScene,
    ElectricalFixtureCm,
    FloorPlanRenderRequest,
    RenderWarning,
)
from ikea_agent.tools.image_analysis.models import (
    DepthEstimationToolResult,
    ObjectDetectionToolResult,
)

_ = (
    AgentCatalogItem.agent_key,
    AgentCatalogItem.ag_ui_path,
    AgentCatalogItem.web_path,
    AgentDescription.prompt_markdown,
    Room3DSnapshotCamera.position_m,
    Room3DSnapshotCamera.target_m,
    Room3DSnapshotCamera.fov_deg,
    Room3DSnapshotLighting.light_fixture_ids,
    Room3DSnapshotLighting.emphasized_light_count,
    Room3DSnapshotContext.captured_at,
    GoogleEmbeddingSettings.google_task_type,
    RecentTraceReportListResponse.traces,
    TraceReportCreateResponse.beads_epic_id,
    TraceReportCreateResponse.beads_task_id,
    AppSettings.embedding_provider,
    AppSettings.rerank_candidate_limit,
    ThreadRecord.owner_id,
    ThreadRecord.updated_at,
    MessageArchiveRecord.archive_version,
    SearchResultRecord.search_result_id,
    RunHistoryRepository.load_archived_all_messages_json,
    RerankedItem.rank_before,
    products_canonical,
    product_embeddings,
    product_embedding_neighbors,
    DuckDBImpl,
    connect_db,
    run_sql_file,
    RetrievalResult.filter_pass_reasons,
    RetrievalResult.rank_explanation,
    SearchQueryInput.purpose,
    BundleProposalItemInput,
    BundleValidationResult,
    BundleProposalLineItem,
    BundleProposalToolResult,
    ElectricalFixtureCm,
    BaselineFloorPlanScene,
    DetailedFloorPlanScene.tagged_items,
    FloorPlanRenderRequest.render_preset,
    RenderWarning.severity,
    RenderWarning.entity_id,
    ObjectDetectionToolResult.image_width_px,
    ObjectDetectionToolResult.image_height_px,
    DepthEstimationToolResult.parameters_used,
)
