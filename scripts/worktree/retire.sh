#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Retire a worktree safely.

Usage:
  scripts/worktree/retire.sh [--worktree <path>] [--force]
EOF
}

WORKTREE_PATH=""
FORCE_FLAG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --force)
      FORCE_FLAG=1
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

if [[ -z "${WORKTREE_PATH}" ]]; then
  WORKTREE_PATH="$(git rev-parse --show-toplevel)"
fi

if [[ ! -d "${WORKTREE_PATH}" ]]; then
  printf 'Worktree path does not exist: %s\n' "${WORKTREE_PATH}" >&2
  exit 1
fi

WORKTREE_ENV="${WORKTREE_PATH}/.tmp_untracked/worktree.env"
if [[ -f "${WORKTREE_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${WORKTREE_ENV}"
  if [[ -n "${BACKEND_PORT:-}" ]]; then
    lsof -tiTCP:"${BACKEND_PORT}" -sTCP:LISTEN | xargs kill 2>/dev/null || true
  fi
  if [[ -n "${UI_PORT:-}" ]]; then
    lsof -tiTCP:"${UI_PORT}" -sTCP:LISTEN | xargs kill 2>/dev/null || true
  fi
fi

CURRENT_ROOT="$(git rev-parse --show-toplevel)"
if [[ "${CURRENT_ROOT}" == "${WORKTREE_PATH}" ]]; then
  cd "${WORKTREE_PATH}/.."
fi

if (( FORCE_FLAG == 1 )); then
  bd worktree remove "${WORKTREE_PATH}" --force
else
  bd worktree remove "${WORKTREE_PATH}"
fi

printf 'Removed worktree: %s\n' "${WORKTREE_PATH}"
