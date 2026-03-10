#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Create/claim a task worktree without manual bd/worktree exploration.

Usage:
  scripts/worktree/start-task.sh (--issue <id> | --query <text>) --slot <0-99> [--epic <epic-id>] [--slug <slug>] [--root <path>] [--dry-run] [--skip-ui-install]
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "${cmd}" >&2
    exit 1
  fi
}

bd_cmd() {
  bd --allow-stale "$@"
}

to_slug() {
  local input="$1"
  local slug
  slug="$(printf '%s' "${input}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  slug="${slug:0:40}"
  slug="${slug%-}"
  if [[ -z "${slug}" ]]; then
    slug="task"
  fi
  printf '%s\n' "${slug}"
}

ISSUE_ID=""
QUERY=""
SLOT=""
EPIC_ID=""
SLUG=""
ROOT_PATH="${TMPDIR%/}/tal_maria_ikea-worktrees"
DRY_RUN=0
SKIP_UI_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE_ID="$2"
      shift 2
      ;;
    --query)
      QUERY="$2"
      shift 2
      ;;
    --slot)
      SLOT="$2"
      shift 2
      ;;
    --epic)
      EPIC_ID="$2"
      shift 2
      ;;
    --slug)
      SLUG="$2"
      shift 2
      ;;
    --root)
      ROOT_PATH="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-ui-install)
      SKIP_UI_INSTALL=1
      shift
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

if [[ -n "${ISSUE_ID}" && -n "${QUERY}" ]] || [[ -z "${ISSUE_ID}" && -z "${QUERY}" ]]; then
  printf 'Provide exactly one of --issue or --query.\n' >&2
  usage
  exit 1
fi

if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
  printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
  exit 1
fi

require_cmd bd
require_cmd git
require_cmd jq

REPO_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "${REPO_ROOT}" ]]; then
  printf 'Unable to determine repository root.\n' >&2
  exit 1
fi

if [[ -z "${ISSUE_ID}" ]]; then
  matches_json="$(bd_cmd ready --json | jq --arg q "${QUERY}" '
    [ .[]
      | . + { _match: (((.title // "") + "\n" + (.description // "")) | ascii_downcase | contains($q | ascii_downcase)) }
      | select(._match)
      | del(._match)
    ]
  ')"
  match_count="$(printf '%s' "${matches_json}" | jq 'length')"
  if [[ "${match_count}" -eq 0 ]]; then
    printf 'No ready issue matched query: %s\n' "${QUERY}" >&2
    exit 1
  fi
  if [[ "${match_count}" -gt 1 ]]; then
    printf 'Query matched multiple ready issues. Re-run with --issue <id>:\n' >&2
    printf '%s\n' "${matches_json}" | jq -r '.[] | "- \(.id): \(.title)"' >&2
    exit 1
  fi
  ISSUE_ID="$(printf '%s' "${matches_json}" | jq -r '.[0].id')"
fi

issue_json="$(bd_cmd show "${ISSUE_ID}" --json | jq '.[0]')"
if [[ -z "${issue_json}" || "${issue_json}" == "null" ]]; then
  printf 'Issue not found: %s\n' "${ISSUE_ID}" >&2
  exit 1
fi

ISSUE_TITLE="$(printf '%s' "${issue_json}" | jq -r '.title')"
ISSUE_TYPE="$(printf '%s' "${issue_json}" | jq -r '.issue_type')"

if [[ -z "${EPIC_ID}" ]]; then
  if [[ "${ISSUE_TYPE}" == "epic" ]]; then
    EPIC_ID="${ISSUE_ID}"
  elif [[ "${ISSUE_ID}" == *.* ]]; then
    EPIC_ID="${ISSUE_ID%%.*}"
  else
    # Fallback: for standalone tasks, use task id as branch/worktree scope.
    EPIC_ID="${ISSUE_ID}"
  fi
fi

if [[ -z "${SLUG}" ]]; then
  SLUG="$(to_slug "${ISSUE_TITLE}")"
fi

WORKTREE_NAME="${EPIC_ID}-${SLUG}"
WORKTREE_PATH="${ROOT_PATH%/}/${WORKTREE_NAME}"
BRANCH_NAME="epic/${EPIC_ID}-${SLUG}"
BACKEND_PORT=$((8100 + SLOT))
UI_PORT=$((3100 + SLOT))

if (( DRY_RUN == 1 )); then
  cat <<DRYRUN
Issue: ${ISSUE_ID}
Epic: ${EPIC_ID}
Slug: ${SLUG}
Branch: ${BRANCH_NAME}
Path: ${WORKTREE_PATH}
Slot: ${SLOT}
Backend port: ${BACKEND_PORT}
UI port: ${UI_PORT}
DRYRUN
  exit 0
fi

mkdir -p "${ROOT_PATH}"
if [[ -e "${WORKTREE_PATH}" ]]; then
  printf 'Worktree path already exists: %s\n' "${WORKTREE_PATH}" >&2
  exit 1
fi

bd_cmd worktree create "${WORKTREE_PATH}" --branch "${BRANCH_NAME}" --json >/dev/null
bd_cmd update "${ISSUE_ID}" --status in_progress --json >/dev/null || true

bootstrap_cmd=("${WORKTREE_PATH}/scripts/worktree/bootstrap.sh" --slot "${SLOT}" --canonical-root "${REPO_ROOT}")
if (( SKIP_UI_INSTALL == 1 )); then
  bootstrap_cmd+=(--skip-ui-install)
fi
bash "${bootstrap_cmd[@]}"

cat <<NEXT

Worktree ready.
Issue: ${ISSUE_ID}
Path: ${WORKTREE_PATH}
Branch: ${BRANCH_NAME}
Backend port: ${BACKEND_PORT}
UI port: ${UI_PORT}

Next:
  cd ${WORKTREE_PATH}
NEXT
