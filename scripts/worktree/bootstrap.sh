#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Bootstrap a worktree with Dockerized dependencies and environment variables.

Usage:
  scripts/worktree/bootstrap.sh --slot <0-99> [--canonical-root <path>] [--skip-ui-install]
EOF
}

SLOT=""
CANONICAL_ROOT=""
SKIP_UI_INSTALL=0

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKTREE_ROOT="$(git -C "${SCRIPT_DIR}/../.." rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${WORKTREE_ROOT}" ]]; then
  printf 'Unable to determine worktree root from %s.\n' "${SCRIPT_DIR}" >&2
  exit 1
fi

if [[ -z "${CANONICAL_ROOT}" ]]; then
  CANONICAL_ROOT="$(resolve_canonical_root "${WORKTREE_ROOT}")"
fi

cd "${WORKTREE_ROOT}"

mkdir -p .tmp_untracked/runtime .tmp_untracked/artifacts .tmp_untracked/comments .tmp_untracked/traces

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

bash "${WORKTREE_ROOT}/scripts/worktree/deps.sh" up \
  --slot "${SLOT}" \
  --canonical-root "${CANONICAL_ROOT}" \
  --worktree-root "${WORKTREE_ROOT}"

BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))
POSTGRES_PORT=$((15432 + SLOT))
WORKTREE_ENV="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"

cat > "${WORKTREE_ENV}" <<EOF
export AGENT_SLOT=${SLOT}
export CANONICAL_ROOT=${CANONICAL_ROOT}
export BACKEND_PORT=${BACKEND_PORT}
export PORT=${BACKEND_PORT}
export UI_PORT=${UI_PORT}
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=${POSTGRES_PORT}
export POSTGRES_DB=ikea_agent
export POSTGRES_USER=ikea
export POSTGRES_PASSWORD=ikea
export DATABASE_URL=postgresql+psycopg://ikea:ikea@127.0.0.1:${POSTGRES_PORT}/ikea_agent
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
Postgres port: ${POSTGRES_PORT}
UI deps installed: $([[ "${SKIP_UI_INSTALL}" == "0" ]] && printf 'yes' || printf 'no (skipped)')
EOF
