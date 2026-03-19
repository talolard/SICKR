"""Add catalog and ops schemas for Dockerized local dependencies.

Revision ID: 20260319_0005
Revises: 20260312_0004
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

APP_SCHEMA = "app"
CATALOG_SCHEMA = "catalog"
OPS_SCHEMA = "ops"

# revision identifiers, used by Alembic.
revision: str = "20260319_0005"
down_revision: str | Sequence[str] | None = "20260312_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema changes."""

    op.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG_SCHEMA}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {OPS_SCHEMA}")

    op.create_table(
        "products_canonical",
        sa.Column("canonical_product_key", sa.String(length=128), primary_key=True),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("unique_id", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("product_name", sa.String(length=512), nullable=True),
        sa.Column("display_title", sa.String(length=512), nullable=True),
        sa.Column("product_type", sa.String(length=256), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("main_category", sa.String(length=256), nullable=True),
        sa.Column("sub_category", sa.String(length=256), nullable=True),
        sa.Column("dimensions_text", sa.String(length=256), nullable=True),
        sa.Column("width_cm", sa.Float(), nullable=True),
        sa.Column("depth_cm", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("price_eur", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=32), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.Column("badge", sa.String(length=256), nullable=True),
        sa.Column("online_sellable", sa.Boolean(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=False), nullable=True),
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_products_canonical_country",
        "products_canonical",
        ["country"],
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_products_canonical_main_category",
        "products_canonical",
        ["main_category"],
        schema=CATALOG_SCHEMA,
    )

    op.create_table(
        "product_embeddings",
        sa.Column("canonical_product_key", sa.String(length=128), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("embedding_vector", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedded_text", sa.Text(), nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("canonical_product_key", "embedding_model"),
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_product_embeddings_model",
        "product_embeddings",
        ["embedding_model"],
        schema=CATALOG_SCHEMA,
    )

    op.create_table(
        "product_embedding_neighbors",
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("source_product_key", sa.String(length=128), nullable=False),
        sa.Column("neighbor_product_key", sa.String(length=128), nullable=False),
        sa.Column("neighbor_rank", sa.Integer(), nullable=True),
        sa.Column("cosine_similarity", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint(
            "embedding_model",
            "source_product_key",
            "neighbor_product_key",
        ),
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_product_embedding_neighbors_model_source",
        "product_embedding_neighbors",
        ["embedding_model", "source_product_key"],
        schema=CATALOG_SCHEMA,
    )

    op.create_table(
        "product_images",
        sa.Column("image_asset_key", sa.String(length=512), primary_key=True),
        sa.Column("canonical_product_key", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=False),
        sa.Column("image_rank", sa.Integer(), nullable=True),
        sa.Column("is_og_image", sa.Boolean(), nullable=False),
        sa.Column("image_role", sa.String(length=128), nullable=True),
        sa.Column("storage_backend_kind", sa.String(length=64), nullable=False),
        sa.Column("storage_locator", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("canonical_image_url", sa.Text(), nullable=True),
        sa.Column("provenance", sa.String(length=128), nullable=True),
        sa.Column("crawl_run_id", sa.String(length=128), nullable=True),
        sa.Column("source_page_url", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=128), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_product_images_product_id",
        "product_images",
        ["product_id"],
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        "ix_catalog_product_images_canonical_product_key",
        "product_images",
        ["canonical_product_key"],
        schema=CATALOG_SCHEMA,
    )

    op.create_table(
        "seed_state",
        sa.Column("system_name", sa.String(length=128), primary_key=True),
        sa.Column("version", sa.String(length=256), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema=OPS_SCHEMA,
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_table("seed_state", schema=OPS_SCHEMA)
    op.drop_index(
        "ix_catalog_product_images_canonical_product_key",
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.drop_index(
        "ix_catalog_product_images_product_id",
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.drop_table("product_images", schema=CATALOG_SCHEMA)
    op.drop_index(
        "ix_catalog_product_embedding_neighbors_model_source",
        table_name="product_embedding_neighbors",
        schema=CATALOG_SCHEMA,
    )
    op.drop_table("product_embedding_neighbors", schema=CATALOG_SCHEMA)
    op.drop_index(
        "ix_catalog_product_embeddings_model",
        table_name="product_embeddings",
        schema=CATALOG_SCHEMA,
    )
    op.drop_table("product_embeddings", schema=CATALOG_SCHEMA)
    op.drop_index(
        "ix_catalog_products_canonical_main_category",
        table_name="products_canonical",
        schema=CATALOG_SCHEMA,
    )
    op.drop_index(
        "ix_catalog_products_canonical_country",
        table_name="products_canonical",
        schema=CATALOG_SCHEMA,
    )
    op.drop_table("products_canonical", schema=CATALOG_SCHEMA)
