#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Manage Dockerized local dependencies for one worktree slot.

Usage:
  scripts/worktree/deps.sh <up|down|reset|reseed|status|ensure-postgres|ensure-milvus> \
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

ensure_postgres() {
  compose_postgres up -d postgres
  wait_for_postgres
  migrate_postgres
  env -u VIRTUAL_ENV uv run python -m ikea_agent.docker_deps.seed_postgres \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --repo-root "${CANONICAL_ROOT}"
}

ensure_milvus() {
  compose_milvus up -d milvus
  wait_for_milvus
  env -u VIRTUAL_ENV uv run python -m ikea_agent.docker_deps.prepare_milvus \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --state-file "${MILVUS_STATE_FILE}"
}

force_reseed() {
  migrate_postgres
  env -u VIRTUAL_ENV uv run python -m ikea_agent.docker_deps.seed_postgres \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --repo-root "${CANONICAL_ROOT}" \
    --force
  env -u VIRTUAL_ENV uv run python -m ikea_agent.docker_deps.prepare_milvus \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --state-file "${MILVUS_STATE_FILE}" \
    --force
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
  status)
    require_docker
    printf 'Worktree root: %s\n' "${WORKTREE_ROOT}"
    printf 'Canonical root: %s\n' "${CANONICAL_ROOT}"
    printf 'Slot: %s\n' "${SLOT}"
    printf 'Backend/UI ports: %s / %s\n' "${BACKEND_PORT}" "${UI_PORT}"
    printf 'DATABASE_URL: %s\n' "${POSTGRES_DATABASE_URL}"
    printf 'MILVUS_URI: http://127.0.0.1:%s\n' "${MILVUS_PORT}"
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
