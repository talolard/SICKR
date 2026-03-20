#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Prepare and run the human-owned local dev environment in the canonical checkout.

Usage:
  scripts/human_dev.sh

Environment:
  HUMAN_DEV_SLOT   Reserved slot for the human-owned runtime (default: 90)
EOF
}

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

ensure_slot_not_claimed_by_other_worktree() {
  local env_file=""
  local slot_value=""
  local worktree_path=""
  while IFS= read -r worktree_path; do
    if [[ "${worktree_path}" == "${WORKTREE_ROOT}" ]]; then
      continue
    fi
    env_file="${worktree_path}/.tmp_untracked/worktree.env"
    if [[ ! -f "${env_file}" ]]; then
      continue
    fi
    slot_value="$(sed -n 's/^export AGENT_SLOT=//p' "${env_file}" | head -n 1)"
    if [[ "${slot_value}" == "${SLOT}" ]]; then
      printf 'Reserved human slot %s is already claimed by worktree %s.\n' "${SLOT}" "${worktree_path}" >&2
      printf 'Agents must use a different slot via make agent-start.\n' >&2
      exit 1
    fi
  done < <(git -C "${WORKTREE_ROOT}" worktree list --porcelain | awk '/^worktree / {print substr($0, 10)}')
}

backend_is_running() {
  curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/agents" >/dev/null 2>&1
}

ui_is_running() {
  curl -fsS "http://127.0.0.1:${UI_PORT}/agents/search" >/dev/null 2>&1
}

clear_stale_ui_lock() {
  local lock_path="${WORKTREE_ROOT}/ui/.next/dev/lock"
  if [[ -f "${lock_path}" ]] && ! ui_is_running; then
    rm -f "${lock_path}"
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SLOT="${HUMAN_DEV_SLOT:-90}"

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'HUMAN_DEV_SLOT must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${WORKTREE_ROOT}" ]]; then
  printf 'Unable to determine repository root.\n' >&2
  exit 1
fi

CANONICAL_ROOT="$(resolve_canonical_root "${WORKTREE_ROOT}")"
if [[ "${WORKTREE_ROOT}" != "${CANONICAL_ROOT}" ]]; then
  printf 'make dev human is reserved for the canonical checkout at %s.\n' "${CANONICAL_ROOT}" >&2
  printf 'Agents must use make agent-start in a dedicated worktree instead.\n' >&2
  exit 1
fi

ensure_slot_not_claimed_by_other_worktree

BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))

printf 'Preparing human dev slot %s in %s\n' "${SLOT}" "${WORKTREE_ROOT}"
printf 'Backend: http://127.0.0.1:%s\n' "${BACKEND_PORT}"
printf 'UI: http://127.0.0.1:%s/agents/search\n' "${UI_PORT}"
printf 'Postgres: repo-shared service bootstrapped via scripts/worktree/bootstrap.sh\n'

bash "${WORKTREE_ROOT}/scripts/worktree/bootstrap.sh" \
  --slot "${SLOT}" \
  --canonical-root "${CANONICAL_ROOT}"

WORKTREE_ENV="${WORKTREE_ROOT}/.tmp_untracked/worktree.env"
if [[ -f "${WORKTREE_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${WORKTREE_ENV}"
  printf 'Database: %s\n' "${DATABASE_URL}"
fi

if backend_is_running && ui_is_running; then
  printf 'Human dev is already running.\n'
  printf 'Open http://127.0.0.1:%s/agents/search\n' "${UI_PORT}"
  exit 0
fi

if backend_is_running; then
  clear_stale_ui_lock
  printf 'Backend already running on reserved slot %s; starting UI only.\n' "${SLOT}"
  exec "${WORKTREE_ROOT}/scripts/worktree/run-dev.sh" --mode ui
fi

if ui_is_running; then
  printf 'UI already running on reserved slot %s; starting backend only.\n' "${SLOT}"
  exec "${WORKTREE_ROOT}/scripts/worktree/run-dev.sh" --mode backend
fi

clear_stale_ui_lock
printf 'Starting human dev servers on reserved slot %s\n' "${SLOT}"
exec "${WORKTREE_ROOT}/scripts/worktree/run-dev.sh"
