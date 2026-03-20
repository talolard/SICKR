#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Manage Dockerized local dependencies for one worktree.

Usage:
  scripts/worktree/deps.sh <up|down|reset|reseed|status|ensure-postgres|build-snapshot|fetch-snapshot> \
    [--slot <0-99>] [--canonical-root <path>] [--worktree-root <path>]
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

sanitize_identifier() {
  local value="$1"
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '_')"
  value="$(printf '%s' "${value}" | sed -E 's/^_+//; s/_+$//; s/_+/_/g')"
  if [[ -z "${value}" ]]; then
    value="worktree"
  fi
  printf '%s\n' "${value}"
}

hash_text() {
  local value="$1"
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "${value}" | shasum -a 256 | awk '{print substr($1, 1, 8)}'
    return 0
  fi
  printf '%s' "${value}" | cksum | awk '{print $1}'
}

worktree_database_name() {
  local basename_slug=""
  local suffix=""
  basename_slug="$(sanitize_identifier "$(basename "${WORKTREE_ROOT}")")"
  basename_slug="${basename_slug:0:40}"
  suffix="$(hash_text "${WORKTREE_ROOT}")"
  printf 'ikea_wt_%s_%s\n' "${basename_slug}" "${suffix}"
}

sql_quote_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

acquire_lock() {
  local name="$1"
  local lock_dir="${LOCK_ROOT}/${name}.lock"
  local attempts=0
  while ! mkdir "${lock_dir}" 2>/dev/null; do
    attempts=$((attempts + 1))
    if (( attempts > 120 )); then
      printf 'Timed out waiting for lock: %s\n' "${lock_dir}" >&2
      exit 1
    fi
    sleep 1
  done
  printf '%s\n' "${lock_dir}"
}

release_lock() {
  local lock_dir="$1"
  rmdir "${lock_dir}" 2>/dev/null || true
}

with_lock() {
  local name="$1"
  shift
  local lock_dir=""
  local status=0
  lock_dir="$(acquire_lock "${name}")"
  set +e
  "$@"
  status=$?
  set -e
  release_lock "${lock_dir}"
  return "${status}"
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
  CANONICAL_ROOT="${WORKTREE_ROOT}"
fi
CANONICAL_ROOT="$(resolve_canonical_root "${CANONICAL_ROOT}")"

if [[ -z "${SLOT}" ]]; then
  ENV_FILE="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"
  if [[ -f "${ENV_FILE}" ]]; then
    SLOT="$(sed -n 's/^export AGENT_SLOT=//p' "${ENV_FILE}" | head -n 1)"
  fi
fi

if [[ -n "${SLOT}" ]]; then
  if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
    printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
    exit 1
  fi
  SLOT_PADDED="$(printf '%02d' "${SLOT}")"
  BACKEND_PORT=$((8100 + SLOT))
  UI_PORT=$((3100 + SLOT))
else
  SLOT_PADDED=""
  BACKEND_PORT=""
  UI_PORT=""
fi

POSTGRES_PROJECT="ikea-shared-postgres"
POSTGRES_PORT=15432
POSTGRES_ADMIN_DB="postgres"
POSTGRES_TEMPLATE_DB="ikea_snapshot_template"
POSTGRES_USER="ikea"
POSTGRES_PASSWORD="ikea"
POSTGRES_VOLUME_NAME="${POSTGRES_PROJECT}-postgres-data"
WORKTREE_DB_NAME="$(worktree_database_name)"
SHARED_POSTGRES_ROOT="${CANONICAL_ROOT}/.tmp_untracked/shared-postgres"
LOCK_ROOT="${SHARED_POSTGRES_ROOT}/locks"
POSTGRES_ENV_DIR="${SHARED_POSTGRES_ROOT}/compose"
POSTGRES_ENV_FILE="${POSTGRES_ENV_DIR}/compose.env"
SNAPSHOT_ROOT="${SHARED_POSTGRES_ROOT}/snapshots"
SNAPSHOT_LATEST_FILE="${SNAPSHOT_ROOT}/latest.json"
POSTGRES_RUNTIME_ENV_DIR="${WORKTREE_ROOT}/.tmp_untracked/docker-deps/postgres"
POSTGRES_RUNTIME_ENV_FILE="${POSTGRES_RUNTIME_ENV_DIR}/runtime.env"
POSTGRES_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${WORKTREE_DB_NAME}"
POSTGRES_COMPOSE_FILE="${WORKTREE_ROOT}/docker/compose.postgres.yml"

mkdir -p "${POSTGRES_ENV_DIR}" "${SNAPSHOT_ROOT}" "${LOCK_ROOT}" "${POSTGRES_RUNTIME_ENV_DIR}"

cat > "${POSTGRES_ENV_FILE}" <<EOF
POSTGRES_PORT=${POSTGRES_PORT}
POSTGRES_DB=${POSTGRES_ADMIN_DB}
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

admin_psql() {
  compose_postgres exec -T postgres psql \
    -v ON_ERROR_STOP=1 \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_ADMIN_DB}" \
    "$@"
}

database_psql() {
  local database_name="$1"
  shift
  compose_postgres exec -T postgres psql \
    -v ON_ERROR_STOP=1 \
    -U "${POSTGRES_USER}" \
    -d "${database_name}" \
    "$@"
}

run_admin_sql() {
  admin_psql -Atqc "$1"
}

run_database_sql() {
  local database_name="$1"
  local sql="$2"
  database_psql "${database_name}" -Atqc "${sql}"
}

wait_for_postgres() {
  local attempts=0
  until compose_postgres exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_ADMIN_DB}" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if (( attempts > 60 )); then
      printf 'Shared Postgres did not become ready on port %s.\n' "${POSTGRES_PORT}" >&2
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

snapshot_artifact_ready() {
  local artifact_path=""
  local manifest_path=""
  if [[ ! -f "${SNAPSHOT_LATEST_FILE}" ]]; then
    return 1
  fi
  artifact_path="$(snapshot_field "artifact_path" 2>/dev/null || true)"
  manifest_path="$(snapshot_field "manifest_path" 2>/dev/null || true)"
  [[ -n "${artifact_path}" && -f "${artifact_path}" && -n "${manifest_path}" && -f "${manifest_path}" ]]
}

fetch_snapshot_artifact() {
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.fetch_postgres_snapshot \
    --repo-root "${WORKTREE_ROOT}" \
    --output-root "${SNAPSHOT_ROOT}"
}

require_snapshot_artifact() {
  if snapshot_artifact_ready; then
    return 0
  fi
  printf 'Snapshot cache missing or incomplete in %s; attempting to fetch a published artifact.\n' \
    "${SNAPSHOT_ROOT}" >&2
  if fetch_snapshot_artifact >/dev/null && snapshot_artifact_ready; then
    return 0
  fi
  printf 'No usable snapshot artifact is available. Build one locally with scripts/worktree/deps.sh build-snapshot --slot %s, or make sure gh is authenticated so the published CI artifact can be fetched.\n' \
    "${SLOT:-<slot>}" >&2
  exit 1
}

latest_snapshot_version() {
  require_snapshot_artifact
  snapshot_field "snapshot_version"
}

latest_snapshot_artifact_path() {
  require_snapshot_artifact
  snapshot_field "artifact_path"
}

database_exists() {
  local database_name="$1"
  local quoted_name=""
  quoted_name="$(sql_quote_literal "${database_name}")"
  [[ "$(run_admin_sql "SELECT 1 FROM pg_database WHERE datname = '${quoted_name}'")" == "1" ]]
}

database_snapshot_version() {
  local database_name="$1"
  run_database_sql "${database_name}" \
    "SELECT version FROM ops.seed_state WHERE system_name = 'postgres_snapshot'" 2>/dev/null || true
}

database_catalog_row_count() {
  local database_name="$1"
  local row_count=""
  row_count="$(
    run_database_sql "${database_name}" \
      "SELECT count(*) FROM catalog.products_canonical" 2>/dev/null || true
  )"
  if [[ -z "${row_count}" ]]; then
    row_count=0
  fi
  printf '%s\n' "${row_count}"
}

clear_snapshot_state() {
  local database_name="$1"
  run_database_sql "${database_name}" \
    "DELETE FROM ops.seed_state WHERE system_name = 'postgres_snapshot'" >/dev/null 2>&1 || true
}

database_requires_snapshot_restore() {
  local database_name="$1"
  local latest_version=""
  local current_version=""
  local row_count=""
  latest_version="$(latest_snapshot_version)"
  current_version="$(database_snapshot_version "${database_name}")"
  row_count="$(database_catalog_row_count "${database_name}")"
  if [[ "${current_version}" != "${latest_version}" ]]; then
    return 0
  fi
  if [[ "${row_count}" == "0" ]]; then
    return 0
  fi
  return 1
}

terminate_database_connections() {
  local database_name="$1"
  local quoted_name=""
  quoted_name="$(sql_quote_literal "${database_name}")"
  run_admin_sql \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${quoted_name}' AND pid <> pg_backend_pid()" \
    >/dev/null 2>&1 || true
}

drop_database_if_exists() {
  local database_name="$1"
  terminate_database_connections "${database_name}"
  run_admin_sql "DROP DATABASE IF EXISTS \"${database_name}\"" >/dev/null
}

create_database() {
  local database_name="$1"
  run_admin_sql "CREATE DATABASE \"${database_name}\" OWNER \"${POSTGRES_USER}\"" >/dev/null
}

create_database_from_template() {
  local database_name="$1"
  run_admin_sql \
    "CREATE DATABASE \"${database_name}\" WITH TEMPLATE \"${POSTGRES_TEMPLATE_DB}\" OWNER \"${POSTGRES_USER}\"" \
    >/dev/null
}

restore_postgres_snapshot_into_database() {
  local database_name="$1"
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
    printf 'Could not resolve the shared Postgres container for restore.\n' >&2
    exit 1
  fi
  docker cp "${artifact_path}" "${container_id}:/tmp/postgres.dump"
  compose_postgres exec -T postgres pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "${POSTGRES_USER}" \
    -d "${database_name}" \
    /tmp/postgres.dump
  restored_version="$(database_snapshot_version "${database_name}")"
  if [[ "${restored_version}" != "${snapshot_version}" ]]; then
    printf 'Snapshot restore completed, but expected version %s and found %s.\n' \
      "${snapshot_version}" \
      "${restored_version}" >&2
    exit 1
  fi
}

shared_postgres_running() {
  [[ -n "$(compose_postgres ps -q postgres 2>/dev/null | tr -d '\n')" ]]
}

ensure_shared_postgres_service() {
  compose_postgres up -d postgres >/dev/null
  wait_for_postgres
}

ensure_template_database_locked() {
  ensure_shared_postgres_service
  if database_exists "${POSTGRES_TEMPLATE_DB}" && ! database_requires_snapshot_restore "${POSTGRES_TEMPLATE_DB}"; then
    return 0
  fi
  drop_database_if_exists "${POSTGRES_TEMPLATE_DB}"
  create_database "${POSTGRES_TEMPLATE_DB}"
  restore_postgres_snapshot_into_database "${POSTGRES_TEMPLATE_DB}"
}

ensure_template_database() {
  require_snapshot_artifact
  with_lock "template-db" ensure_template_database_locked
}

ensure_worktree_database_locked() {
  if database_exists "${WORKTREE_DB_NAME}" && ! database_requires_snapshot_restore "${WORKTREE_DB_NAME}"; then
    return 0
  fi
  drop_database_if_exists "${WORKTREE_DB_NAME}"
  create_database_from_template "${WORKTREE_DB_NAME}"
}

prepare_worktree_database_from_template_locked() {
  ensure_template_database_locked
  ensure_worktree_database_locked
}

ensure_worktree_database_under_db_lock() {
  with_lock "template-db" prepare_worktree_database_from_template_locked
}

ensure_worktree_database() {
  local database_lock_name=""
  database_lock_name="worktree-db-$(hash_text "${WORKTREE_DB_NAME}")"
  with_lock "${database_lock_name}" ensure_worktree_database_under_db_lock
}

recreate_worktree_database_locked() {
  drop_database_if_exists "${WORKTREE_DB_NAME}"
  create_database_from_template "${WORKTREE_DB_NAME}"
}

recreate_worktree_database_from_template_locked() {
  ensure_template_database_locked
  recreate_worktree_database_locked
}

recreate_worktree_database_under_db_lock() {
  with_lock "template-db" recreate_worktree_database_from_template_locked
}

recreate_worktree_database() {
  local database_lock_name=""
  database_lock_name="worktree-db-$(hash_text "${WORKTREE_DB_NAME}")"
  with_lock "${database_lock_name}" recreate_worktree_database_under_db_lock
}

remaining_worktree_database_count() {
  run_admin_sql "SELECT count(*) FROM pg_database WHERE datname LIKE 'ikea_wt_%'"
}

write_runtime_env() {
  cat > "${POSTGRES_RUNTIME_ENV_FILE}" <<EOF
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=${POSTGRES_PORT}
export POSTGRES_DB=${WORKTREE_DB_NAME}
export POSTGRES_DB_NAME=${WORKTREE_DB_NAME}
export POSTGRES_USER=${POSTGRES_USER}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
export DATABASE_URL=${POSTGRES_DATABASE_URL}
export SHARED_POSTGRES_ROOT=${SHARED_POSTGRES_ROOT}
export SHARED_POSTGRES_TEMPLATE_DB=${POSTGRES_TEMPLATE_DB}
EOF
}

ensure_postgres() {
  ensure_shared_postgres_service
  ensure_worktree_database
  migrate_postgres
  write_runtime_env
}

release_worktree_database() {
  local database_lock_name=""
  database_lock_name="worktree-db-$(hash_text "${WORKTREE_DB_NAME}")"
  with_lock "${database_lock_name}" drop_database_if_exists "${WORKTREE_DB_NAME}"
}

force_reseed() {
  migrate_postgres
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.seed_postgres \
    --database-url "${POSTGRES_DATABASE_URL}" \
    --repo-root "${WORKTREE_ROOT}" \
    --force
  clear_snapshot_state "${WORKTREE_DB_NAME}"
  write_runtime_env
}

build_snapshot() {
  local snapshot_output_root="${SNAPSHOT_ROOT}"
  local snapshot_builder_port=""
  local snapshot_validator_port=""
  local snapshot_project_prefix=""
  if [[ -z "${SLOT}" ]]; then
    printf 'build-snapshot requires --slot <0-99>.\n' >&2
    exit 1
  fi
  snapshot_builder_port=$((25432 + SLOT))
  snapshot_validator_port=$((26432 + SLOT))
  snapshot_project_prefix="ikea-slot-${SLOT_PADDED}-snapshot"
  env -u VIRTUAL_ENV uv run python -m scripts.docker_deps.build_postgres_snapshot \
    --repo-root "${WORKTREE_ROOT}" \
    --output-root "${snapshot_output_root}" \
    --builder-port "${snapshot_builder_port}" \
    --validator-port "${snapshot_validator_port}" \
    --project-prefix "${snapshot_project_prefix}"
}

status_command() {
  printf 'Worktree root: %s\n' "${WORKTREE_ROOT}"
  printf 'Canonical root: %s\n' "${CANONICAL_ROOT}"
  if [[ -n "${SLOT}" ]]; then
    printf 'Slot: %s\n' "${SLOT}"
    printf 'Backend/UI ports: %s / %s\n' "${BACKEND_PORT}" "${UI_PORT}"
  fi
  printf 'Shared Postgres port: %s\n' "${POSTGRES_PORT}"
  printf 'Worktree database: %s\n' "${WORKTREE_DB_NAME}"
  printf 'DATABASE_URL: %s\n' "${POSTGRES_DATABASE_URL}"
  printf 'Template database: %s\n' "${POSTGRES_TEMPLATE_DB}"
  printf 'Snapshot cache root: %s\n' "${SNAPSHOT_ROOT}"
  if snapshot_artifact_ready; then
    printf 'Latest snapshot version: %s\n' "$(latest_snapshot_version)"
    printf 'Latest snapshot source: %s\n' "$(snapshot_field "source_kind")"
  fi
  if shared_postgres_running; then
    printf 'Shared service: running\n'
    printf 'Template snapshot version: %s\n' "$(database_snapshot_version "${POSTGRES_TEMPLATE_DB}")"
    if database_exists "${WORKTREE_DB_NAME}"; then
      printf 'Current DB snapshot version: %s\n' "$(database_snapshot_version "${WORKTREE_DB_NAME}")"
    else
      printf 'Current DB snapshot version: not created\n'
    fi
    compose_postgres ps || true
  else
    printf 'Shared service: stopped\n'
  fi
}

case "${COMMAND}" in
  ensure-postgres)
    require_docker
    ensure_postgres
    ;;
  up)
    require_docker
    ensure_postgres
    ;;
  down)
    require_docker
    if shared_postgres_running; then
      release_worktree_database
      if [[ "$(remaining_worktree_database_count)" == "0" ]]; then
        compose_postgres down --remove-orphans >/dev/null
      fi
    fi
    rm -f "${POSTGRES_RUNTIME_ENV_FILE}"
    ;;
  reset)
    require_docker
    ensure_shared_postgres_service
    ensure_template_database
    recreate_worktree_database
    migrate_postgres
    write_runtime_env
    ;;
  reseed)
    require_docker
    ensure_postgres
    force_reseed
    ;;
  build-snapshot)
    require_docker
    build_snapshot
    ;;
  fetch-snapshot)
    fetch_snapshot_artifact
    ;;
  status)
    require_docker
    status_command
    ;;
  *)
    printf 'Unknown command: %s\n' "${COMMAND}" >&2
    usage
    exit 1
    ;;
esac
