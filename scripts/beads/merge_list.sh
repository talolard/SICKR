#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
List merge queue items intended for merger-agent runs.

Usage:
  scripts/beads/merge_list.sh [--json] [--parent <epic-id>] [--assignee <name>]
USAGE
}

PARENT_ID="tal_maria_ikea-0uk"
ASSIGNEE="merger-agent"
JSON_OUTPUT=0

bd_cmd() {
  bd --allow-stale "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    --parent)
      PARENT_ID="$2"
      shift 2
      ;;
    --assignee)
      ASSIGNEE="$2"
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

raw_json="$(bd_cmd list --json --parent "${PARENT_ID}" --status blocked --assignee "${ASSIGNEE}" --limit 0)"

sorted_json="$(printf '%s' "${raw_json}" | jq '
  map(select(.issue_type == "merge-request" or ((.labels // []) | index("merge-request") != null)))
  | sort_by((.priority // 9), (.created_at // ""), .id)
')"

if (( JSON_OUTPUT == 1 )); then
  printf '%s\n' "${sorted_json}"
  exit 0
fi

printf 'Merge queue parent: %s\n' "${PARENT_ID}"
printf 'Assignee: %s\n\n' "${ASSIGNEE}"

count="$(printf '%s' "${sorted_json}" | jq 'length')"
if [[ "${count}" -eq 0 ]]; then
  printf 'No blocked merge-request items found.\n'
  exit 0
fi

printf '%-20s %-8s %-12s %s\n' 'ID' 'P' 'STATUS' 'TITLE'
printf '%-20s %-8s %-12s %s\n' '--------------------' '--------' '------------' '------------------------------'
printf '%s\n' "${sorted_json}" | jq -r '.[] | [
  .id,
  (.priority|tostring),
  .status,
  .title
] | @tsv' | while IFS=$'\t' read -r id priority status title; do
  printf '%-20s %-8s %-12s %s\n' "${id}" "${priority}" "${status}" "${title}"
done
