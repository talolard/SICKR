#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Manage Dockerized local dependencies for one worktree slot.

Usage:
  scripts/worktree/deps.sh <up|down|reset|reseed|status|ensure-postgres|ensure-milvus|build-snapshot> \
    [--slot <0-99>] [--canonical-root <path>] [--worktree-root <path>] [--include-global]
EOF
}

COMMAND="${1:-}"
if [[ -z "${COMMAND}" ]]; then
  usage
  exit 1
fi
shift || true

SLOT="${AGENT_SLOT:-}"
CANONICAL_ROOT=""
WORKTREE_ROOT=""
INCLUDE_GLOBAL=0

resolve_canonical_root() {
  local repo_root="$1"
  local primary_root=""
  primary_root="$(
    git -C "${repo_root}" worktree list --porcelain 2>/dev/null \
      | sed -n 's/^worktree //p' \
      | head -n 1
  )"
  if [[ -n "${primary_root}" ]]; then
    printf '%s\n' "${primary_root}"
    return 0
  fi
  printf '%s\n' "${repo_root}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slot)
      SLOT="$2"
      shift 2
      ;;
    --canonical-root)
      CANONICAL_ROOT="$2"
      shift 2
      ;;
    --worktree-root)
      WORKTREE_ROOT="$2"
      shift 2
      ;;
    --include-global)
      INCLUDE_GLOBAL=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${WORKTREE_ROOT}" ]]; then
  WORKTREE_ROOT="$(git rev-parse --show-toplevel)"
fi

if [[ -z "${CANONICAL_ROOT}" ]]; then
  CANONICAL_ROOT="$(resolve_canonical_root "${WORKTREE_ROOT}")"
fi

if [[ -z "${SLOT}" ]]; then
  ENV_FILE="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"
  if [[ -f "${ENV_FILE}" ]]; then
    SLOT="$(sed -n 's/^export AGENT_SLOT=//p' "${ENV_FILE}" | head -n 1)"
  fi
fi

if [[ -z "${SLOT}" ]]; then
  printf 'Missing slot. Pass --slot or bootstrap the worktree first.\n' >&2
  exit 1
fi

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

SLOT_PADDED="$(printf '%02d' "${SLOT}")"
POSTGRES_PROJECT="ikea-slot-${SLOT_PADDED}"
GLOBAL_PROJECT="ikea-global"
POSTGRES_PORT=$((15432 + SLOT))
POSTGRES_DB="ikea_agent"
POSTGRES_USER="ikea"
POSTGRES_PASSWORD="ikea"
POSTGRES_VOLUME_NAME="${POSTGRES_PROJECT}-postgres-data"
MILVUS_PORT=19530
MILVUS_HTTP_PORT=9091
MILVUS_VOLUME_NAME="${GLOBAL_PROJECT}-milvus-data"
BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))
POSTGRES_ENV_DIR="${WORKTREE_ROOT}/.tmp_untracked/docker-deps/postgres"
GLOBAL_ENV_DIR="${CANONICAL_ROOT}/.tmp_untracked/docker-deps/global"
POSTGRES_ENV_FILE="${POSTGRES_ENV_DIR}/compose.env"
MILVUS_ENV_FILE="${GLOBAL_ENV_DIR}/compose.env"
MILVUS_STATE_FILE="${GLOBAL_ENV_DIR}/milvus_seed_state.json"
SNAPSHOT_ROOT="${CANONICAL_ROOT}/.tmp_untracked/docker-deps/snapshots"
SNAPSHOT_LATEST_FILE="${SNAPSHOT_ROOT}/latest.json"
POSTGRES_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${POSTGRES_DB}"
POSTGRES_COMPOSE_FILE="${WORKTREE_ROOT}/docker/compose.postgres.yml"
MILVUS_COMPOSE_FILE="${WORKTREE_ROOT}/docker/compose.milvus.yml"

mkdir -p "${POSTGRES_ENV_DIR}" "${GLOBAL_ENV_DIR}"

cat > "${POSTGRES_ENV_FILE}" <<EOF
POSTGRES_PORT=${POSTGRES_PORT}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_VOLUME_NAME=${POSTGRES_VOLUME_NAME}
EOF

cat > "${MILVUS_ENV_FILE}" <<EOF
MILVUS_PORT=${MILVUS_PORT}
MILVUS_HTTP_PORT=${MILVUS_HTTP_PORT}
MILVUS_VOLUME_NAME=${MILVUS_VOLUME_NAME}
EOF

compose_postgres() {
  docker compose \
    --env-file "${POSTGRES_ENV_FILE}" \
    -f "${POSTGRES_COMPOSE_FILE}" \
    -p "${POSTGRES_PROJECT}" \
    "$@"
}

compose_milvus() {
  docker compose \
    --env-file "${MILVUS_ENV_FILE}" \
    -f "${MILVUS_COMPOSE_FILE}" \
    -p "${GLOBAL_PROJECT}" \
    "$@"
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'Docker CLI is not installed.\n' >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    printf 'Docker daemon is not running. Start Docker Desktop or your local daemon first.\n' >&2
    exit 1
  fi
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

wait_for_milvus() {
  local attempts=0
  until curl -fsS "http://127.0.0.1:${MILVUS_HTTP_PORT}/healthz" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if (( attempts > 90 )); then
      printf 'Milvus did not become healthy on port %s.\n' "${MILVUS_HTTP_PORT}" >&2
      return 1
    fi
    sleep 1
  done
}

migrate_postgres() {
  ALEMBIC_DATABASE_URL="${POSTGRES_DATABASE_URL}" \
    env -u VIRTUAL_ENV uv run alembic upgrade head
}

snapshot_field() {
  local field="$1"
  env -u VIRTUAL_ENV uv run python -c 'import json, sys; print(json.loads(open(sys.argv[1], encoding="utf-8").read())[sys.argv[2]])' \
    "${SNAPSHOT_LATEST_FILE}" \
    "${field}"
}

require_snapshot_artifact() {
  if [[ ! -f "${SNAPSHOT_LATEST_FILE}" ]]; then
    printf 'Missing snapshot metadata at %s. Build it first with scripts/worktree/deps.sh build-snapshot --slot %s.\n' \
      "${SNAPSHOT_LATEST_FILE}" \
      "${SLOT}" >&2
    exit 1
  fi
}

latest_snapshot_version() {
  require_snapshot_artifact
  snapshot_field "snapshot_version"
}

latest_snapshot_artifact_path() {
  require_snapshot_artifact
  snapshot_field "artifact_path"
}

current_snapshot_version() {
  compose_postgres exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atqc \
    "SELECT version FROM ops.seed_state WHERE system_name = 'postgres_snapshot'" 2>/dev/null || true
}

catalog_row_count() {
  local row_count=""
  row_count="$(
    compose_postgres exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atqc \
      "SELECT count(*) FROM catalog.products_canonical" 2>/dev/null || true
  )"
  if [[ -z "${row_count}" ]]; then
    row_count=0
  fi
  printf '%s\n' "${row_count}"
}

clear_snapshot_state() {
  compose_postgres exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atqc \
    "DELETE FROM ops.seed_state WHERE system_name = 'postgres_snapshot'" >/dev/null 2>&1 || true
}

postgres_requires_snapshot_restore() {
  local latest_version=""
  local current_version=""
  local row_count=""
  latest_version="$(latest_snapshot_version)"
  current_version="$(current_snapshot_version)"
  row_count="$(catalog_row_count)"
  if [[ "${current_version}" != "${latest_version}" ]]; then
    return 0
  fi
  if [[ "${row_count}" == "0" ]]; then
    return 0
  fi
  return 1
}

restore_postgres_snapshot() {
  local artifact_path=""
  local container_id=""
  local restored_version=""
  local snapshot_version=""
  artifact_path="$(latest_snapshot_artifact_path)"
  snapshot_version="$(latest_snapshot_version)"
  if [[ ! -f "${artifact_path}" ]]; then
    printf 'Snapshot artifact is missing: %s\n' "${artifact_path}" >&2
    exit 1
  fi
  container_id="$(compose_postgres ps -q postgres | tr -d '\n')"
  if [[ -z "${container_id}" ]]; then
    printf 'Could not resolve the slot-local Postgres container for restore.\n' >&2
    exit 1
  fi
  docker cp "${artifact_path}" "${container_id}:/tmp/postgres.dump"
  compose_postgres exec -T postgres pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    /tmp/postgres.dump
  restored_version="$(current_snapshot_version)"
  if [[ "${restored_version}" != "${snapshot_version}" ]]; then
    printf 'Snapshot restore completed, but expected version %s and found %s.\n' \
      "${snapshot_version}" \
      "${restored_version}" >&2
    exit 1
  fi
}

ensure_postgres() {
  compose_postgres up -d postgres
  wait_for_postgres
  if postgres_requires_snapshot_restore; then
    restore_postgres_snapshot
  fi
  migrate_postgres
}

ensure_milvus() {
  compose_milvus up -d milvus
  wait_for_milvus
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.prepare_milvus \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --state-file "${MILVUS_STATE_FILE}"
}

force_reseed() {
  migrate_postgres
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.seed_postgres \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --repo-root "${CANONICAL_ROOT}" \
    --force
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.prepare_milvus \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --state-file "${MILVUS_STATE_FILE}" \
    --force
  clear_snapshot_state
}

build_snapshot() {
  local snapshot_output_root="${CANONICAL_ROOT}/.tmp_untracked/docker-deps/snapshots"
  local snapshot_builder_port=$((25432 + SLOT))
  local snapshot_validator_port=$((26432 + SLOT))
  local snapshot_project_prefix="ikea-slot-${SLOT_PADDED}-snapshot"
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.build_postgres_snapshot \
    --repo-root "${WORKTREE_ROOT}" \
    --output-root "${snapshot_output_root}" \
    --builder-port "${snapshot_builder_port}" \
    --validator-port "${snapshot_validator_port}" \
    --project-prefix "${snapshot_project_prefix}"
}

case "${COMMAND}" in
  ensure-postgres)
    require_docker
    ensure_postgres
    ;;
  ensure-milvus)
    require_docker
    compose_milvus up -d milvus
    wait_for_milvus
    ;;
  up)
    require_docker
    ensure_postgres
    ensure_milvus
    ;;
  down)
    require_docker
    compose_postgres down --remove-orphans
    if (( INCLUDE_GLOBAL == 1 )); then
      compose_milvus down --remove-orphans
    fi
    ;;
  reset)
    require_docker
    compose_postgres down --volumes --remove-orphans
    ensure_postgres
    ;;
  reseed)
    require_docker
    compose_postgres up -d postgres
    wait_for_postgres
    compose_milvus up -d milvus
    wait_for_milvus
    force_reseed
    ;;
  build-snapshot)
    require_docker
    build_snapshot
    ;;
  status)
    require_docker
    printf 'Worktree root: %s\n' "${WORKTREE_ROOT}"
    printf 'Canonical root: %s\n' "${CANONICAL_ROOT}"
    printf 'Slot: %s\n' "${SLOT}"
    printf 'Backend/UI ports: %s / %s\n' "${BACKEND_PORT}" "${UI_PORT}"
    printf 'DATABASE_URL: %s\n' "${POSTGRES_DATABASE_URL}"
    printf 'MILVUS_URI: http://127.0.0.1:%s\n' "${MILVUS_PORT}"
    if [[ -f "${SNAPSHOT_LATEST_FILE}" ]]; then
      printf 'Latest snapshot version: %s\n' "$(latest_snapshot_version)"
    fi
    printf 'Current DB snapshot version: %s\n' "$(current_snapshot_version)"
    compose_postgres ps || true
    compose_milvus ps || true
    if [[ -f "${MILVUS_STATE_FILE}" ]]; then
      printf '\nMilvus seed state:\n'
      cat "${MILVUS_STATE_FILE}"
    fi
    ;;
  *)
    printf 'Unknown command: %s\n' "${COMMAND}" >&2
    usage
    exit 1
    ;;
esac
