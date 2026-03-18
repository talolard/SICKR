#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Bootstrap a worktree with isolated runtime state and environment variables.

Usage:
  scripts/worktree/bootstrap.sh --slot <0-99> [--canonical-root <path>] [--force-db-refresh] [--skip-ui-install]
EOF
}

copy_with_clone_fallback() {
  local src="$1"
  local dst="$2"
  if cp -c "${src}" "${dst}" 2>/dev/null; then
    return 0
  fi
  cp "${src}" "${dst}"
}

SLOT=""
CANONICAL_ROOT=""
FORCE_DB_REFRESH=0
SKIP_UI_INSTALL=0

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
    --force-db-refresh)
      FORCE_DB_REFRESH=1
      shift 1
      ;;
    --skip-ui-install)
      SKIP_UI_INSTALL=1
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

if [[ -z "${SLOT}" ]]; then
  usage
  exit 1
fi

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

if [[ -z "${CANONICAL_ROOT}" ]]; then
  CANONICAL_ROOT="$(git rev-parse --show-toplevel)"
fi

WORKTREE_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "${WORKTREE_ROOT}" ]]; then
  printf 'Unable to determine worktree root.\n' >&2
  exit 1
fi

cd "${WORKTREE_ROOT}"

mkdir -p .tmp_untracked/runtime .tmp_untracked/artifacts .tmp_untracked/comments

if [[ ! -f ".env" ]]; then
  if [[ -f "${CANONICAL_ROOT}/.env" ]]; then
    cp "${CANONICAL_ROOT}/.env" .env
  elif [[ -f ".env.example" ]]; then
    cp ".env.example" .env
  else
    printf 'No .env source found. Expected %s/.env or local .env.example.\n' "${CANONICAL_ROOT}" >&2
    exit 1
  fi
fi

CANONICAL_DUCKDB="${CANONICAL_ROOT}/data/ikea.duckdb"
CANONICAL_MILVUS="${CANONICAL_ROOT}/data/milvus_lite.db"
LOCAL_DUCKDB="${WORKTREE_ROOT}/.tmp_untracked/runtime/ikea.duckdb"
LOCAL_MILVUS="${WORKTREE_ROOT}/.tmp_untracked/runtime/milvus_lite.db"

if [[ ! -f "${CANONICAL_DUCKDB}" ]]; then
  printf 'Canonical DuckDB not found: %s\n' "${CANONICAL_DUCKDB}" >&2
  exit 1
fi

if [[ ! -f "${CANONICAL_MILVUS}" ]]; then
  printf 'Canonical Milvus Lite DB not found: %s\n' "${CANONICAL_MILVUS}" >&2
  exit 1
fi

if (( FORCE_DB_REFRESH == 1 )) || [[ ! -f "${LOCAL_DUCKDB}" ]]; then
  copy_with_clone_fallback "${CANONICAL_DUCKDB}" "${LOCAL_DUCKDB}"
fi

if (( FORCE_DB_REFRESH == 1 )) || [[ ! -f "${LOCAL_MILVUS}" ]]; then
  copy_with_clone_fallback "${CANONICAL_MILVUS}" "${LOCAL_MILVUS}"
fi

BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))
WORKTREE_ENV="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"

cat > "${WORKTREE_ENV}" <<EOF
export AGENT_SLOT=${SLOT}
export BACKEND_PORT=${BACKEND_PORT}
export PORT=${BACKEND_PORT}
export UI_PORT=${UI_PORT}
export DUCKDB_PATH=${LOCAL_DUCKDB}
export MILVUS_LITE_URI=${LOCAL_MILVUS}
export ARTIFACT_ROOT_DIR=${WORKTREE_ROOT}/.tmp_untracked/artifacts
export FEEDBACK_ROOT_DIR=${WORKTREE_ROOT}/.tmp_untracked/comments
export PY_AG_UI_URL=http://127.0.0.1:${BACKEND_PORT}/ag-ui/
EOF

env -u VIRTUAL_ENV uv sync --all-groups

if (( SKIP_UI_INSTALL == 0 )); then
  make ui-install
fi

cat <<EOF
Bootstrapped worktree: ${WORKTREE_ROOT}
Environment file: ${WORKTREE_ENV}
Backend port: ${BACKEND_PORT}
UI port: ${UI_PORT}
UI deps installed: $([[ "${SKIP_UI_INSTALL}" == "0" ]] && printf 'yes' || printf 'no (skipped)')
EOF
