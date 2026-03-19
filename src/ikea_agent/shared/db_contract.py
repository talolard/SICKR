"""Shared database and storage contract constants for local runtime state."""

from __future__ import annotations

CATALOG_SCHEMA = "catalog"
APP_SCHEMA = "app"
OPS_SCHEMA = "ops"

POSTGRES_SEED_SYSTEM = "postgres_catalog"
IMAGE_CATALOG_SEED_SYSTEM = "image_catalog"
POSTGRES_SNAPSHOT_SYSTEM = "postgres_snapshot"

PRODUCT_EMBEDDING_DIMENSIONS = 3072
PRODUCT_EMBEDDING_DISTANCE_METRIC = "cosine"
PRODUCT_EMBEDDING_VECTOR_INDEX_NAME = "ix_catalog_product_embeddings_halfvec_hnsw"
PRODUCT_EMBEDDING_VECTOR_OPCLASS = "halfvec_cosine_ops"
PRODUCT_IMAGE_PRODUCT_ID_LOOKUP_INDEX_NAME = "ix_catalog_product_images_product_lookup"
PRODUCT_IMAGE_CANONICAL_KEY_LOOKUP_INDEX_NAME = "ix_catalog_product_images_canonical_product_lookup"

LOCAL_IMAGE_STORAGE_BACKEND = "local_shared_root"
REMOTE_IMAGE_STORAGE_BACKEND = "remote_object_store"
