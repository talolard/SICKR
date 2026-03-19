"""Shared database and storage contract constants for local runtime state."""

from __future__ import annotations

CATALOG_SCHEMA = "catalog"
APP_SCHEMA = "app"
OPS_SCHEMA = "ops"

POSTGRES_SEED_SYSTEM = "postgres_catalog"
IMAGE_CATALOG_SEED_SYSTEM = "image_catalog"

LOCAL_IMAGE_STORAGE_BACKEND = "local_shared_root"
REMOTE_IMAGE_STORAGE_BACKEND = "remote_object_store"
