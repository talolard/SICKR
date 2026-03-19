"""Shared database and storage contract constants for local runtime state."""

from __future__ import annotations

CATALOG_SCHEMA = "catalog"
APP_SCHEMA = "app"
OPS_SCHEMA = "ops"

POSTGRES_SEED_SYSTEM = "postgres_catalog"
IMAGE_CATALOG_SEED_SYSTEM = "image_catalog"
POSTGRES_SNAPSHOT_SYSTEM = "postgres_snapshot"

PRODUCT_EMBEDDING_DIMENSIONS = 256
PRODUCT_EMBEDDING_DISTANCE_METRIC = "cosine"
PRODUCT_EMBEDDING_VECTOR_INDEX_NAME = "ix_catalog_product_embeddings_vector_hnsw"
PRODUCT_EMBEDDING_VECTOR_OPCLASS = "vector_cosine_ops"

LOCAL_IMAGE_STORAGE_BACKEND = "local_shared_root"
REMOTE_IMAGE_STORAGE_BACKEND = "remote_object_store"
