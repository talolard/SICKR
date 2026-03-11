#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
List merge queue items with CI-aware filtering.

Default output is merge-ready items only (required checks passing).

Usage:
  scripts/beads/merge_list.sh [--json] [--all | --failing] [--parent <epic-id>] [--assignee <name>] [--repo <owner/repo>] [--suggest-assignee <name>]
USAGE
}

PARENT_ID="tal_maria_ikea-0uk"
ASSIGNEE="merger-agent"
JSON_OUTPUT=0
SHOW_ALL=0
SHOW_FAILING=0
REPO_OVERRIDE=""
SUGGEST_ASSIGNEE="codex-agent"

bd_cmd() {
  bd --allow-stale "$@"
}

extract_pr_url() {
  local description="$1"
  printf '%s\n' "$description" | rg -o 'https://github\.com/[^[:space:]]+/[^[:space:]]+/pull/[0-9]+' -m1 || true
}

extract_pr_repo() {
  local pr_url="$1"
  printf '%s\n' "$pr_url" | sed -E 's#https://github.com/([^/]+/[^/]+)/pull/[0-9]+#\1#'
}

extract_pr_number() {
  local pr_url="$1"
  printf '%s\n' "$pr_url" | sed -E 's#.*/pull/([0-9]+).*#\1#'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    --all)
      SHOW_ALL=1
      shift
      ;;
    --failing)
      SHOW_FAILING=1
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
    --repo)
      REPO_OVERRIDE="$2"
      shift 2
      ;;
    --suggest-assignee)
      SUGGEST_ASSIGNEE="$2"
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

if (( SHOW_ALL == 1 && SHOW_FAILING == 1 )); then
  echo "Use at most one of --all or --failing." >&2
  exit 1
fi

raw_json="$(bd_cmd list --json --parent "${PARENT_ID}" --status blocked --assignee "${ASSIGNEE}" --limit 0)"

sorted_json="$(printf '%s' "${raw_json}" | jq '
  map(select(.issue_type == "merge-request" or ((.labels // []) | index("merge-request") != null)))
  | sort_by((.priority // 9), (.created_at // ""), .id)
')"

count_all="$(printf '%s' "$sorted_json" | jq 'length')"
if [[ "$count_all" -eq 0 ]]; then
  if (( JSON_OUTPUT == 1 )); then
    printf '[]\n'
  else
    printf 'Merge queue parent: %s\n' "${PARENT_ID}"
    printf 'Assignee: %s\n\n' "${ASSIGNEE}"
    printf 'No blocked merge-request items found.\n'
  fi
  exit 0
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required for merge CI filtering." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for merge CI filtering." >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "gh CLI is not authenticated. Run 'gh auth login' and retry." >&2
  exit 1
fi

enriched_tmp="$(mktemp)"
while IFS= read -r item; do
  id="$(printf '%s' "$item" | jq -r '.id')"
  title="$(printf '%s' "$item" | jq -r '.title')"
  status="$(printf '%s' "$item" | jq -r '.status')"
  priority="$(printf '%s' "$item" | jq '.priority // 9')"
  description="$(printf '%s' "$item" | jq -r '.description // ""')"

  pr_url="$(extract_pr_url "$description")"
  pr_number=""
  pr_repo=""
  ci_state=""
  ci_summary=""
  failing_checks='[]'

  if [[ -z "$pr_url" ]]; then
    ci_state="no-pr-link"
    ci_summary="No PR URL found in merge bead description."
  else
    pr_number="$(extract_pr_number "$pr_url")"
    if [[ -n "$REPO_OVERRIDE" ]]; then
      pr_repo="$REPO_OVERRIDE"
    else
      pr_repo="$(extract_pr_repo "$pr_url")"
    fi

    checks_tmp="$(mktemp)"
    checks_err_tmp="$(mktemp)"
    if gh pr checks "$pr_number" --repo "$pr_repo" --required --json name,state,bucket,workflow,link >"$checks_tmp" 2>"$checks_err_tmp"; then
      checks_json="$(cat "$checks_tmp")"
      total_checks="$(printf '%s' "$checks_json" | jq 'length')"
      fail_count="$(printf '%s' "$checks_json" | jq '[.[] | select(.bucket == "fail")] | length')"
      pending_count="$(printf '%s' "$checks_json" | jq '[.[] | select(.bucket == "pending" or .bucket == "cancel" or .bucket == "skipping")] | length')"
      passing_count="$(printf '%s' "$checks_json" | jq '[.[] | select(.bucket == "pass")] | length')"
      failing_checks="$(printf '%s' "$checks_json" | jq '[.[] | select(.bucket != "pass") | {name, bucket, state, workflow, link}]')"

      if [[ "$total_checks" -eq 0 ]]; then
        ci_state="no-required-checks"
        ci_summary="No required checks returned by GitHub for this PR."
      elif [[ "$fail_count" -gt 0 || "$pending_count" -gt 0 ]]; then
        ci_state="not-green"
        ci_summary="Required checks not green (pass=${passing_count}, fail=${fail_count}, pending_or_other=${pending_count})."
      else
        ci_state="green"
        ci_summary="Required checks are green (${passing_count} pass)."
      fi
    else
      check_err="$(tr '\n' ' ' < "$checks_err_tmp")"
      if [[ "$check_err" == *"no checks reported"* ]]; then
        ci_state="no-checks-reported"
        ci_summary="GitHub reports no checks for this PR branch."
      else
        ci_state="check-query-error"
        ci_summary="Failed to query PR checks: ${check_err}"
      fi
    fi
    rm -f "$checks_tmp" "$checks_err_tmp"
  fi

  assignment_cmd="bd update ${id} --assignee ${SUGGEST_ASSIGNEE} --json"

  jq -n \
    --arg id "$id" \
    --arg title "$title" \
    --arg status "$status" \
    --arg pr_url "$pr_url" \
    --arg pr_repo "$pr_repo" \
    --arg pr_number "$pr_number" \
    --arg ci_state "$ci_state" \
    --arg ci_summary "$ci_summary" \
    --arg assignment_cmd "$assignment_cmd" \
    --argjson priority "$priority" \
    --argjson failing_checks "$failing_checks" \
    '{
      id: $id,
      title: $title,
      status: $status,
      priority: $priority,
      pr_url: (if $pr_url == "" then null else $pr_url end),
      pr_repo: (if $pr_repo == "" then null else $pr_repo end),
      pr_number: (if $pr_number == "" then null else ($pr_number | tonumber) end),
      ci_state: $ci_state,
      ci_summary: $ci_summary,
      failing_checks: $failing_checks,
      suggested_assignment_command: $assignment_cmd
    }' >> "$enriched_tmp"
  printf '\n' >> "$enriched_tmp"
done < <(printf '%s' "$sorted_json" | jq -c '.[]')

enriched_json="$(jq -s '.' "$enriched_tmp")"
rm -f "$enriched_tmp"

if (( SHOW_ALL == 1 )); then
  filtered_json="$enriched_json"
elif (( SHOW_FAILING == 1 )); then
  filtered_json="$(printf '%s' "$enriched_json" | jq '[.[] | select(.ci_state != "green")]')"
else
  filtered_json="$(printf '%s' "$enriched_json" | jq '[.[] | select(.ci_state == "green")]')"
fi

if (( JSON_OUTPUT == 1 )); then
  printf '%s\n' "$filtered_json"
  exit 0
fi

printf 'Merge queue parent: %s\n' "${PARENT_ID}"
printf 'Assignee: %s\n' "${ASSIGNEE}"
if (( SHOW_ALL == 1 )); then
  printf 'View: all merge-request items (CI-enriched)\n\n'
elif (( SHOW_FAILING == 1 )); then
  printf 'View: non-green merge-request items (required checks)\n\n'
else
  printf 'View: green-only merge-request items (required checks)\n\n'
fi

count="$(printf '%s' "$filtered_json" | jq 'length')"
if [[ "$count" -eq 0 ]]; then
  printf 'No items in current view.\n'
else
  printf '%-20s %-4s %-20s %-8s %s\n' 'ID' 'P' 'CI' 'PR' 'TITLE'
  printf '%-20s %-4s %-20s %-8s %s\n' '--------------------' '----' '--------------------' '--------' '------------------------------'
  printf '%s\n' "$filtered_json" | jq -r '.[] | [
    .id,
    (.priority|tostring),
    .ci_state,
    (if .pr_number == null then "-" else ("#" + (.pr_number|tostring)) end),
    .title
  ] | @tsv' | while IFS=$'\t' read -r id priority ci_state pr title; do
    printf '%-20s %-4s %-20s %-8s %s\n' "$id" "$priority" "$ci_state" "$pr" "$title"
  done
fi

non_green_count="$(printf '%s' "$enriched_json" | jq '[.[] | select(.ci_state != "green")] | length')"
if (( SHOW_FAILING == 1 || SHOW_ALL == 1 )); then
  if [[ "$non_green_count" -gt 0 ]]; then
    printf '\nSuggested assignment commands for non-green items (%s):\n' "$SUGGEST_ASSIGNEE"
    printf '%s\n' "$filtered_json" | jq -r '.[] | select(.ci_state != "green") | "- \(.id): \(.ci_summary)\n  \(.suggested_assignment_command)"'
  fi
else
  if [[ "$non_green_count" -gt 0 ]]; then
    printf '\nNon-green queued items: %s\n' "$non_green_count"
    printf 'Inspect them with: make merge-list-failing\n'
  fi
fi
