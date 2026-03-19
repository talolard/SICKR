#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Run backend/UI dev servers with explicit per-worktree ports.

Usage:
  scripts/worktree/run-dev.sh [--backend-port <port>] [--ui-port <port>] [--mode both|backend|ui]
EOF
}

assert_port_free() {
  local port="$1"
  if lsof -tiTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    printf 'Port %s is already in use.\n' "${port}" >&2
    exit 1
  fi
}

MODE="both"
BACKEND_PORT_ARG=""
UI_PORT_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port)
      BACKEND_PORT_ARG="$2"
      shift 2
      ;;
    --ui-port)
      UI_PORT_ARG="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
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

if [[ "${MODE}" != "both" && "${MODE}" != "backend" && "${MODE}" != "ui" ]]; then
  printf 'Mode must be one of: both, backend, ui. Got: %s\n' "${MODE}" >&2
  exit 1
fi

WORKTREE_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "${WORKTREE_ROOT}" ]]; then
  printf 'Unable to determine worktree root.\n' >&2
  exit 1
fi

WORKTREE_ENV="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"
if [[ ! -f "${WORKTREE_ENV}" ]]; then
  printf 'Missing %s. Run scripts/worktree/bootstrap.sh first.\n' "${WORKTREE_ENV}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${WORKTREE_ENV}"

BACKEND_PORT="${BACKEND_PORT_ARG:-${BACKEND_PORT:-}}"
UI_PORT="${UI_PORT_ARG:-${UI_PORT:-}}"

if [[ -z "${BACKEND_PORT}" || -z "${UI_PORT}" ]]; then
  printf 'Backend/UI ports are not configured.\n' >&2
  exit 1
fi

export DATABASE_URL ARTIFACT_ROOT_DIR FEEDBACK_ROOT_DIR TRACE_ROOT_DIR
export PY_AG_UI_URL="http://127.0.0.1:${BACKEND_PORT}/ag-ui/"

if [[ "${MODE}" == "both" || "${MODE}" == "backend" ]]; then
  assert_port_free "${BACKEND_PORT}"
fi
if [[ "${MODE}" == "both" || "${MODE}" == "ui" ]]; then
  assert_port_free "${UI_PORT}"
fi

if [[ "${MODE}" == "backend" ]]; then
  exec make chat PORT="${BACKEND_PORT}" DATABASE_URL="${DATABASE_URL}"
fi

if [[ "${MODE}" == "ui" ]]; then
  exec make ui-dev-real UI_PORT="${UI_PORT}" PY_AG_UI_URL="${PY_AG_UI_URL}"
fi

trap 'kill 0' INT TERM EXIT
make chat PORT="${BACKEND_PORT}" DATABASE_URL="${DATABASE_URL}" &
sleep 2
make ui-dev-real UI_PORT="${UI_PORT}" PY_AG_UI_URL="${PY_AG_UI_URL}" &
wait
