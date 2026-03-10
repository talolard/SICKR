#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Normalize merge queue to avoid default bd ready pickup.

Usage:
  scripts/beads/merge_normalize.sh [--parent <epic-id>] [--assignee <name>] [--dry-run]
USAGE
}

PARENT_ID="tal_maria_ikea-0uk"
ASSIGNEE="merger-agent"
DRY_RUN=0

bd_cmd() {
  bd --allow-stale "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --parent)
      PARENT_ID="$2"
      shift 2
      ;;
    --assignee)
      ASSIGNEE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
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

if (( DRY_RUN == 1 )); then
  printf 'Dry run: would normalize parent %s and its merge children to blocked + assignee=%s.\n' "${PARENT_ID}" "${ASSIGNEE}"
fi

if (( DRY_RUN == 0 )); then
  bd_cmd update "${PARENT_ID}" --status blocked --assignee "${ASSIGNEE}" --type epic --json >/dev/null
fi

children_json="$(bd_cmd list --json --parent "${PARENT_ID}" --limit 0)"

ids="$(printf '%s' "${children_json}" | jq -r '.[] | .id')"
count=0
converted=0
fallback_labeled=0
for id in ${ids}; do
  count=$((count + 1))
  if (( DRY_RUN == 1 )); then
    printf 'Would normalize child %s\n' "${id}"
    continue
  fi
  if bd_cmd update "${id}" --type merge-request --status blocked --assignee "${ASSIGNEE}" --add-label merge-request --json >/dev/null 2>&1; then
    converted=$((converted + 1))
  else
    # Some bd versions reject type mutation to merge-request; enforce queue isolation regardless.
    bd_cmd update "${id}" --status blocked --assignee "${ASSIGNEE}" --add-label merge-request --json >/dev/null
    fallback_labeled=$((fallback_labeled + 1))
  fi
done

if (( DRY_RUN == 1 )); then
  printf 'Dry run complete. Children considered: %d\n' "${count}"
  exit 0
fi

printf 'Normalized merge queue parent %s and %d children (converted=%d, fallback_labeled=%d).\n' "${PARENT_ID}" "${count}" "${converted}" "${fallback_labeled}"
