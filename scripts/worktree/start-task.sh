#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Create/claim a task worktree without manual bd/worktree exploration.

Usage:
  scripts/worktree/start-task.sh (--issue <id> | --query <text>) [--slot <0-99>] [--mode <full|docs>] [--epic <epic-id>] [--slug <slug>] [--root <path>] [--dry-run] [--skip-ui-install]
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
MODE="full"
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
    --mode)
      MODE="$2"
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

if [[ -n "${ISSUE_ID}" && -n "${QUERY}" ]] || [[ -z "${ISSUE_ID}" && -z "${QUERY}" ]]; then
  printf 'Provide exactly one of --issue or --query.\n' >&2
  usage
  exit 1
fi

if [[ "${MODE}" != "full" && "${MODE}" != "docs" ]]; then
  printf 'Mode must be one of: full, docs. Got: %s\n' "${MODE}" >&2
  exit 1
fi

if [[ "${MODE}" == "full" ]]; then
  if [[ -z "${SLOT}" ]]; then
    usage
    exit 1
  fi
  if ! [[ "${SLOT}" =~ ^[0-9]+$ ]] || (( SLOT < 0 || SLOT > 99 )); then
    printf 'Slot must be an integer between 0 and 99. Got: %s\n' "${SLOT}" >&2
    exit 1
  fi
fi

if [[ "${MODE}" == "docs" && -n "${SLOT}" ]]; then
  printf 'Docs mode does not use slots. Omit --slot.\n' >&2
  exit 1
fi

require_cmd bd
require_cmd git
require_cmd jq

SOURCE_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "${SOURCE_ROOT}" ]]; then
  printf 'Unable to determine repository root.\n' >&2
  exit 1
fi
CANONICAL_ROOT="$(resolve_canonical_root "${SOURCE_ROOT}")"

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
if [[ "${MODE}" == "full" ]]; then
  bash "${SOURCE_ROOT}/scripts/worktree/check-slot.sh" --slot "${SLOT}"
fi

if (( DRY_RUN == 1 )); then
  cat <<DRYRUN
Issue: ${ISSUE_ID}
Epic: ${EPIC_ID}
Slug: ${SLUG}
Branch: ${BRANCH_NAME}
Path: ${WORKTREE_PATH}
Mode: ${MODE}
$(if [[ "${MODE}" == "full" ]]; then
  printf 'Slot: %s\n' "${SLOT}"
  printf 'Backend port: %s\n' "$((8100 + SLOT))"
  printf 'UI port: %s\n' "$((3100 + SLOT))"
fi)
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

bootstrap_cmd=("${WORKTREE_PATH}/scripts/worktree/bootstrap.sh" --mode "${MODE}" --canonical-root "${CANONICAL_ROOT}")
if [[ "${MODE}" == "full" ]]; then
  bootstrap_cmd+=(--slot "${SLOT}")
fi
if [[ "${MODE}" == "full" ]] && (( SKIP_UI_INSTALL == 1 )); then
  bootstrap_cmd+=(--skip-ui-install)
fi
bash "${bootstrap_cmd[@]}"

if [[ "${MODE}" == "full" ]]; then
  BACKEND_PORT=$((8100 + SLOT))
  UI_PORT=$((3100 + SLOT))
  cat <<NEXT

Worktree ready.
Issue: ${ISSUE_ID}
Path: ${WORKTREE_PATH}
Branch: ${BRANCH_NAME}
Mode: ${MODE}
Backend port: ${BACKEND_PORT}
UI port: ${UI_PORT}

Next:
  cd ${WORKTREE_PATH}
NEXT
else
  cat <<NEXT

Worktree ready.
Issue: ${ISSUE_ID}
Path: ${WORKTREE_PATH}
Branch: ${BRANCH_NAME}
Mode: ${MODE}

This worktree is ready for docs/research/spec work.
Upgrade it later with:
  cd ${WORKTREE_PATH}
  bash scripts/worktree/bootstrap.sh --mode full --slot <0-99> --canonical-root ${CANONICAL_ROOT}
NEXT
fi
