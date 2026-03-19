"""SQLAlchemy table definitions for active retrieval runtime tables."""

from __future__ import annotations

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    DOUBLE,
    JSON,
    TEXT,
    TIMESTAMP,
    VARCHAR,
    Column,
    Index,
    MetaData,
    Table,
)

from ikea_agent.shared.db_contract import (
    CATALOG_SCHEMA,
    PRODUCT_EMBEDDING_DIMENSIONS,
    PRODUCT_EMBEDDING_VECTOR_INDEX_NAME,
    PRODUCT_EMBEDDING_VECTOR_OPCLASS,
    PRODUCT_IMAGE_CANONICAL_KEY_LOOKUP_INDEX_NAME,
    PRODUCT_IMAGE_PRODUCT_ID_LOOKUP_INDEX_NAME,
)

retrieval_metadata = MetaData(schema=CATALOG_SCHEMA)
_embedding_vector_type = HALFVEC(PRODUCT_EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite")

products_canonical = Table(
    "products_canonical",
    retrieval_metadata,
    Column("canonical_product_key", VARCHAR, primary_key=True),
    Column("product_id", BIGINT),
    Column("unique_id", VARCHAR),
    Column("country", VARCHAR),
    Column("product_name", VARCHAR),
    Column("display_title", VARCHAR),
    Column("product_type", VARCHAR),
    Column("description_text", VARCHAR),
    Column("main_category", VARCHAR),
    Column("sub_category", VARCHAR),
    Column("dimensions_text", VARCHAR),
    Column("width_cm", DOUBLE),
    Column("depth_cm", DOUBLE),
    Column("height_cm", DOUBLE),
    Column("price_eur", DOUBLE),
    Column("currency", VARCHAR),
    Column("rating", DOUBLE),
    Column("rating_count", BIGINT),
    Column("badge", VARCHAR),
    Column("online_sellable", BOOLEAN),
    Column("url", VARCHAR),
    Column("source_updated_at", TIMESTAMP(timezone=False)),
)

product_embeddings = Table(
    "product_embeddings",
    retrieval_metadata,
    Column("canonical_product_key", VARCHAR, primary_key=True),
    Column("embedding_model", VARCHAR, primary_key=True),
    Column("run_id", VARCHAR),
    Column("embedding_vector", _embedding_vector_type),
    Column("embedded_text", VARCHAR),
    Column("embedded_at", TIMESTAMP(timezone=False)),
)
Index(
    PRODUCT_EMBEDDING_VECTOR_INDEX_NAME,
    product_embeddings.c.embedding_vector,
    postgresql_using="hnsw",
    postgresql_ops={"embedding_vector": PRODUCT_EMBEDDING_VECTOR_OPCLASS},
).ddl_if(dialect="postgresql")

product_images = Table(
    "product_images",
    retrieval_metadata,
    Column("image_asset_key", VARCHAR, primary_key=True),
    Column("canonical_product_key", VARCHAR, nullable=False),
    Column("product_id", VARCHAR, nullable=False),
    Column("image_rank", BIGINT),
    Column("is_og_image", BOOLEAN, nullable=False),
    Column("image_role", VARCHAR),
    Column("storage_backend_kind", VARCHAR, nullable=False),
    Column("storage_locator", TEXT, nullable=False),
    Column("public_url", TEXT),
    Column("local_path", TEXT),
    Column("canonical_image_url", TEXT),
    Column("provenance", VARCHAR),
    Column("crawl_run_id", VARCHAR),
    Column("source_page_url", TEXT),
    Column("sha256", VARCHAR),
    Column("content_type", VARCHAR),
    Column("width_px", BIGINT),
    Column("height_px", BIGINT),
    Column("refreshed_at", TIMESTAMP(timezone=True)),
)
Index(
    PRODUCT_IMAGE_PRODUCT_ID_LOOKUP_INDEX_NAME,
    product_images.c.product_id,
    product_images.c.is_og_image,
    product_images.c.image_rank,
    product_images.c.image_asset_key,
)
Index(
    PRODUCT_IMAGE_CANONICAL_KEY_LOOKUP_INDEX_NAME,
    product_images.c.canonical_product_key,
    product_images.c.is_og_image,
    product_images.c.image_rank,
    product_images.c.image_asset_key,
)

product_embedding_neighbors = Table(
    "product_embedding_neighbors",
    retrieval_metadata,
    Column("embedding_model", VARCHAR, primary_key=True),
    Column("source_product_key", VARCHAR, primary_key=True),
    Column("neighbor_product_key", VARCHAR, primary_key=True),
    Column("neighbor_rank", BIGINT),
    Column("cosine_similarity", DOUBLE),
    Index(
        "ix_product_embedding_neighbors_model_source",
        "embedding_model",
        "source_product_key",
    ),
)
