#!/usr/bin/env bash
set -euo pipefail

SLOT="${1:-0}"
SLOT_PADDED="$(printf '%02d' "${SLOT}")"
POSTGRES_PROJECT="ikea-slot-${SLOT_PADDED}"
POSTGRES_PORT=$((15432 + SLOT))
POSTGRES_DB="ikea_agent"
POSTGRES_USER="ikea"
POSTGRES_PASSWORD="ikea"
POSTGRES_VOLUME_NAME="${POSTGRES_PROJECT}-postgres-data"
POSTGRES_CONTAINER_NAME="${POSTGRES_PROJECT}-postgres-1"
POSTGRES_NETWORK_NAME="${POSTGRES_PROJECT}_default"
POSTGRES_ENV_DIR=".tmp_untracked/docker-deps/postgres"
POSTGRES_ENV_FILE="${POSTGRES_ENV_DIR}/compose.env"
POSTGRES_COMPOSE_FILE="docker/compose.postgres.yml"
DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${POSTGRES_DB}"
PRODUCT_IMAGE_BASE_URL="https://designagent.talperry.com/static/product-images/"

mkdir -p "${POSTGRES_ENV_DIR}"
cat > "${POSTGRES_ENV_FILE}" <<EOF
POSTGRES_PORT=${POSTGRES_PORT}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_VOLUME_NAME=${POSTGRES_VOLUME_NAME}
EOF

compose_postgres() {
  docker compose \
    --env-file "${POSTGRES_ENV_FILE}" \
    -f "${POSTGRES_COMPOSE_FILE}" \
    -p "${POSTGRES_PROJECT}" \
    "$@"
}

wait_for_postgres() {
  local attempts=0
  until compose_postgres exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if (( attempts > 60 )); then
      printf 'Postgres did not become ready on port %s.\n' "${POSTGRES_PORT}" >&2
      return 1
    fi
    sleep 1
  done
}

cleanup() {
  python - <<'PY' \
    "${POSTGRES_ENV_FILE}" \
    "${POSTGRES_COMPOSE_FILE}" \
    "${POSTGRES_PROJECT}" \
    "${POSTGRES_CONTAINER_NAME}" \
    "${POSTGRES_VOLUME_NAME}" \
    "${POSTGRES_NETWORK_NAME}"
from __future__ import annotations

import subprocess
import sys

env_file, compose_file, project_name, container_name, volume_name, network_name = sys.argv[1:]
compose_down = [
    "docker",
    "compose",
    "--env-file",
    env_file,
    "-f",
    compose_file,
    "-p",
    project_name,
    "down",
    "--volumes",
    "--remove-orphans",
]

try:
    subprocess.run(compose_down, check=False, timeout=20)
except subprocess.TimeoutExpired:
    pass

for command in (
    ["docker", "rm", "-f", container_name],
    ["docker", "volume", "rm", "-f", volume_name],
    ["docker", "network", "rm", network_name],
):
    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PY
}

trap cleanup EXIT

compose_postgres down --volumes --remove-orphans >/dev/null 2>&1 || true
compose_postgres up -d postgres
wait_for_postgres

ALEMBIC_DATABASE_URL="${DATABASE_URL}" env -u VIRTUAL_ENV uv run alembic upgrade head
env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.seed_postgres \
  --database-url "${DATABASE_URL}" \
  --repo-root "$PWD" \
  --image-catalog-root "$PWD/tests/fixtures/image_catalog" \
  --image-catalog-run-id "ci-fixture" \
  --product-image-base-url "${PRODUCT_IMAGE_BASE_URL}" \
  --force

export DATABASE_URL
uv run pytest \
  tests/shared/test_migrations.py \
  tests/shared/test_migration_stairway.py
