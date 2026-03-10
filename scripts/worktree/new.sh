#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Create a new temp worktree for an epic and bootstrap isolated runtime state.

Usage:
  scripts/worktree/new.sh --epic <epic-id> --slug <slug> --slot <0-99> [--task <task-id>] [--root <path>]
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "${cmd}" >&2
    exit 1
  fi
}

EPIC_ID=""
SLUG=""
SLOT=""
TASK_ID=""
ROOT_PATH="${TMPDIR%/}/tal_maria_ikea-worktrees"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --epic)
      EPIC_ID="$2"
      shift 2
      ;;
    --slug)
      SLUG="$2"
      shift 2
      ;;
    --slot)
      SLOT="$2"
      shift 2
      ;;
    --task)
      TASK_ID="$2"
      shift 2
      ;;
    --root)
      ROOT_PATH="$2"
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

if [[ -z "${EPIC_ID}" || -z "${SLUG}" || -z "${SLOT}" ]]; then
  usage
  exit 1
fi

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

require_cmd bd
require_cmd git
require_cmd uv

REPO_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "${REPO_ROOT}" ]]; then
  printf 'Unable to determine repository root.\n' >&2
  exit 1
fi

WORKTREE_NAME="${EPIC_ID}-${SLUG}"
WORKTREE_PATH="${ROOT_PATH%/}/${WORKTREE_NAME}"
BRANCH_NAME="epic/${EPIC_ID}-${SLUG}"

mkdir -p "${ROOT_PATH}"
if [[ -e "${WORKTREE_PATH}" ]]; then
  printf 'Worktree path already exists: %s\n' "${WORKTREE_PATH}" >&2
  exit 1
fi

printf 'Creating worktree %s on branch %s\n' "${WORKTREE_PATH}" "${BRANCH_NAME}"
bd worktree create "${WORKTREE_PATH}" --branch "${BRANCH_NAME}" --json >/dev/null

if [[ -n "${TASK_ID}" ]]; then
  bd update "${TASK_ID}" --status in_progress --json >/dev/null || true
fi

printf 'Bootstrapping worktree runtime...\n'
bash "${WORKTREE_PATH}/scripts/worktree/bootstrap.sh" \
  --slot "${SLOT}" \
  --canonical-root "${REPO_ROOT}"

BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))

cat <<EOF

Worktree ready.
Path: ${WORKTREE_PATH}
Branch: ${BRANCH_NAME}
Slot: ${SLOT}
Backend port: ${BACKEND_PORT}
UI port: ${UI_PORT}

Next:
  cd ${WORKTREE_PATH}
  scripts/worktree/run-dev.sh
EOF
