#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Validate that a worktree slot is not already claimed by another worktree or active listener.

Usage:
  scripts/worktree/check-slot.sh --slot <0-99>
EOF
}

SLOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slot)
      SLOT="$2"
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

if [[ -z "${SLOT}" ]]; then
  usage
  exit 1
fi

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))

if lsof -tiTCP:"${BACKEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  printf 'Slot %s unavailable: backend port %s is already in use.\n' "${SLOT}" "${BACKEND_PORT}" >&2
  exit 1
fi

if lsof -tiTCP:"${UI_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  printf 'Slot %s unavailable: UI port %s is already in use.\n' "${SLOT}" "${UI_PORT}" >&2
  exit 1
fi

while IFS= read -r worktree_path; do
  env_file="${worktree_path}/.tmp_untracked/worktree.env"
  if [[ ! -f "${env_file}" ]]; then
    continue
  fi

  slot_value="$(sed -n 's/^export AGENT_SLOT=//p' "${env_file}" | head -n 1)"
  if [[ "${slot_value}" == "${SLOT}" ]]; then
    printf 'Slot %s unavailable: already claimed by worktree %s.\n' "${SLOT}" "${worktree_path}" >&2
    exit 1
  fi
done < <(git worktree list --porcelain | awk '/^worktree / {print substr($0, 10)}')
