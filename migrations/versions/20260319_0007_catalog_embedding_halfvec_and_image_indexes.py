"""Expand catalog embeddings to halfvec and add image lookup indexes.

Revision ID: 20260319_0007
Revises: 20260319_0006
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import HALFVEC, Vector

CATALOG_SCHEMA = "catalog"
OLD_EMBEDDING_VECTOR_DIMENSIONS = 256
NEW_EMBEDDING_VECTOR_DIMENSIONS = 3072
EMBEDDING_VECTOR_PADDING_DIMENSIONS = (
    NEW_EMBEDDING_VECTOR_DIMENSIONS - OLD_EMBEDDING_VECTOR_DIMENSIONS
)
OLD_EMBEDDING_VECTOR_INDEX_NAME = "ix_catalog_product_embeddings_vector_hnsw"
NEW_EMBEDDING_VECTOR_INDEX_NAME = "ix_catalog_product_embeddings_halfvec_hnsw"
OLD_EMBEDDING_VECTOR_OPCLASS = "vector_cosine_ops"
NEW_EMBEDDING_VECTOR_OPCLASS = "halfvec_cosine_ops"
OLD_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME = "ix_catalog_product_images_product_id"
OLD_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME = "ix_catalog_product_images_canonical_product_key"
NEW_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME = "ix_catalog_product_images_product_lookup"
NEW_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME = "ix_catalog_product_images_canonical_product_lookup"
UPGRADE_EMBEDDING_USING_SQL = (
    "CASE "
    "WHEN embedding_vector IS NULL THEN NULL "
    "ELSE translate((array_cat("
    "translate(embedding_vector::text, '[]', '{}')::double precision[], "
    f"array_fill(0::double precision, ARRAY[{EMBEDDING_VECTOR_PADDING_DIMENSIONS}])"
    "))::text, '{}', '[]')::halfvec"
    f"({NEW_EMBEDDING_VECTOR_DIMENSIONS}) "
    "END"
)
DOWNGRADE_EMBEDDING_USING_SQL = (
    "CASE "
    "WHEN embedding_vector IS NULL THEN NULL "
    "ELSE translate((("
    "translate(embedding_vector::text, '[]', '{}')::double precision[]"
    f")[1:{OLD_EMBEDDING_VECTOR_DIMENSIONS}])::text, '{{}}', '[]')::vector"
    f"({OLD_EMBEDDING_VECTOR_DIMENSIONS}) "
    "END"
)

# revision identifiers, used by Alembic.
revision: str = "20260319_0007"
down_revision: str | Sequence[str] | None = "20260319_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade Postgres embedding storage and image lookup indexes."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        OLD_EMBEDDING_VECTOR_INDEX_NAME,
        table_name="product_embeddings",
        schema=CATALOG_SCHEMA,
    )
    op.alter_column(
        "product_embeddings",
        "embedding_vector",
        schema=CATALOG_SCHEMA,
        existing_type=Vector(OLD_EMBEDDING_VECTOR_DIMENSIONS),
        type_=HALFVEC(NEW_EMBEDDING_VECTOR_DIMENSIONS),
        existing_nullable=True,
        postgresql_using=UPGRADE_EMBEDDING_USING_SQL,
    )
    op.create_index(
        NEW_EMBEDDING_VECTOR_INDEX_NAME,
        "product_embeddings",
        ["embedding_vector"],
        unique=False,
        schema=CATALOG_SCHEMA,
        postgresql_using="hnsw",
        postgresql_ops={"embedding_vector": NEW_EMBEDDING_VECTOR_OPCLASS},
    )

    op.drop_index(
        OLD_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME,
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.drop_index(
        OLD_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME,
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        NEW_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME,
        "product_images",
        ["product_id", "is_og_image", "image_rank", "image_asset_key"],
        unique=False,
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        NEW_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME,
        "product_images",
        ["canonical_product_key", "is_og_image", "image_rank", "image_asset_key"],
        unique=False,
        schema=CATALOG_SCHEMA,
    )


def downgrade() -> None:
    """Restore the old vector width and single-column image indexes."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        NEW_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME,
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.drop_index(
        NEW_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME,
        table_name="product_images",
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        OLD_PRODUCT_IMAGE_PRODUCT_ID_INDEX_NAME,
        "product_images",
        ["product_id"],
        unique=False,
        schema=CATALOG_SCHEMA,
    )
    op.create_index(
        OLD_PRODUCT_IMAGE_CANONICAL_KEY_INDEX_NAME,
        "product_images",
        ["canonical_product_key"],
        unique=False,
        schema=CATALOG_SCHEMA,
    )

    op.drop_index(
        NEW_EMBEDDING_VECTOR_INDEX_NAME,
        table_name="product_embeddings",
        schema=CATALOG_SCHEMA,
    )
    op.alter_column(
        "product_embeddings",
        "embedding_vector",
        schema=CATALOG_SCHEMA,
        existing_type=HALFVEC(NEW_EMBEDDING_VECTOR_DIMENSIONS),
        type_=Vector(OLD_EMBEDDING_VECTOR_DIMENSIONS),
        existing_nullable=True,
        postgresql_using=DOWNGRADE_EMBEDDING_USING_SQL,
    )
    op.create_index(
        OLD_EMBEDDING_VECTOR_INDEX_NAME,
        "product_embeddings",
        ["embedding_vector"],
        unique=False,
        schema=CATALOG_SCHEMA,
        postgresql_using="hnsw",
        postgresql_ops={"embedding_vector": OLD_EMBEDDING_VECTOR_OPCLASS},
    )
