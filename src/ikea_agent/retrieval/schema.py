"""SQLAlchemy table definitions for active retrieval runtime tables."""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    DOUBLE,
    JSON,
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
)

retrieval_metadata = MetaData(schema=CATALOG_SCHEMA)
_embedding_vector_type = Vector(PRODUCT_EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite")

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
