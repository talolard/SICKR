"""Upgrade catalog embedding storage to pgvector on Postgres.

Revision ID: 20260319_0006
Revises: 20260319_0005
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

CATALOG_SCHEMA = "catalog"
EMBEDDING_VECTOR_DIMENSIONS = 256
EMBEDDING_VECTOR_INDEX_NAME = "ix_catalog_product_embeddings_vector_hnsw"
EMBEDDING_VECTOR_OPCLASS = "vector_cosine_ops"

# revision identifiers, used by Alembic.
revision: str = "20260319_0006"
down_revision: str | Sequence[str] | None = "20260319_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply pgvector extension and index changes on Postgres."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.alter_column(
        "product_embeddings",
        "embedding_vector",
        schema=CATALOG_SCHEMA,
        existing_type=sa.ARRAY(sa.Float()),
        type_=Vector(EMBEDDING_VECTOR_DIMENSIONS),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN embedding_vector IS NULL THEN NULL "
            "ELSE translate(embedding_vector::text, '{}', '[]')::vector(256) "
            "END"
        ),
    )
    op.create_index(
        EMBEDDING_VECTOR_INDEX_NAME,
        "product_embeddings",
        ["embedding_vector"],
        unique=False,
        schema=CATALOG_SCHEMA,
        postgresql_using="hnsw",
        postgresql_ops={"embedding_vector": EMBEDDING_VECTOR_OPCLASS},
    )


def downgrade() -> None:
    """Revert pgvector storage back to Postgres arrays on Postgres."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        EMBEDDING_VECTOR_INDEX_NAME,
        table_name="product_embeddings",
        schema=CATALOG_SCHEMA,
    )
    op.alter_column(
        "product_embeddings",
        "embedding_vector",
        schema=CATALOG_SCHEMA,
        existing_type=Vector(EMBEDDING_VECTOR_DIMENSIONS),
        type_=sa.ARRAY(sa.Float()),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN embedding_vector IS NULL THEN NULL "
            "ELSE translate(embedding_vector::text, '[]', '{}')::double precision[] "
            "END"
        ),
    )
