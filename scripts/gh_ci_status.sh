#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Summarize latest PR CI status, failing checks/jobs, and check-run annotations.

Usage:
  scripts/gh_ci_status.sh [--pr <number>] [--run <id>] [--repo <owner/repo>] [--limit <n>]

Examples:
  scripts/gh_ci_status.sh
  scripts/gh_ci_status.sh --pr 123
  scripts/gh_ci_status.sh --run 123456789
USAGE
}

PR_NUMBER=""
RUN_ID=""
REPO=""
ANNOTATION_LIMIT=50

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr)
      PR_NUMBER="$2"
      shift 2
      ;;
    --run)
      RUN_ID="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --limit)
      ANNOTATION_LIMIT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required but not found in PATH." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh CLI is not authenticated. Run 'gh auth login' and retry." >&2
  exit 1
fi

if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

if [[ -z "$PR_NUMBER" && -z "$RUN_ID" ]]; then
  PR_NUMBER="$(gh pr view --repo "$REPO" --json number -q .number 2>/dev/null || true)"
fi

resolve_latest_run_for_pr() {
  local pr="$1"
  local head_sha
  head_sha="$(gh pr view "$pr" --repo "$REPO" --json headRefOid -q .headRefOid)"

  gh run list \
    --repo "$REPO" \
    --workflow "PR CI" \
    --event pull_request \
    --limit 100 \
    --json databaseId,headSha,createdAt \
    --jq "map(select(.headSha == \"${head_sha}\")) | sort_by(.createdAt) | last | .databaseId"
}

if [[ -z "$RUN_ID" ]]; then
  if [[ -z "$PR_NUMBER" ]]; then
    echo "No PR context found. Pass --pr <number> or --run <id>." >&2
    exit 1
  fi
  RUN_ID="$(resolve_latest_run_for_pr "$PR_NUMBER")"
fi

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  if [[ -n "$PR_NUMBER" ]]; then
    echo "No PR CI run found for PR #$PR_NUMBER in $REPO." >&2
  else
    echo "No run found." >&2
  fi
  exit 1
fi

echo "Repository: $REPO"
if [[ -n "$PR_NUMBER" ]]; then
  echo "PR: #$PR_NUMBER"
fi
echo "Run ID: $RUN_ID"

echo
echo "Run Summary"
gh run view "$RUN_ID" --repo "$REPO" \
  --json name,event,status,conclusion,url,headBranch,headSha,createdAt,updatedAt \
  --jq '. as $r | [
    "name: \($r.name)",
    "event: \($r.event)",
    "status: \($r.status)",
    "conclusion: \($r.conclusion // "in_progress")",
    "branch: \($r.headBranch)",
    "head_sha: \($r.headSha)",
    "created_at: \($r.createdAt)",
    "updated_at: \($r.updatedAt)",
    "url: \($r.url)"
  ] | .[]'

if [[ -n "$PR_NUMBER" ]]; then
  echo
  echo "PR Check Status"
  gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,workflow,bucket,link \
    --jq '.[] | "[\(.state)] \(.workflow // "") :: \(.name) :: \(.link // "")"' || true
fi

echo
JOBS_JSON="$(gh api "repos/$REPO/actions/runs/$RUN_ID/jobs?per_page=100")"
echo "Jobs"
echo "$JOBS_JSON" | jq -r '.jobs[] | "[\(.conclusion // .status)] \(.name)"'

echo
FAILED_JOBS_JSON="$(echo "$JOBS_JSON" | jq '[.jobs[] | select((.conclusion // "") != "success" and (.conclusion // "") != "skipped")]')"
if [[ "$(echo "$FAILED_JOBS_JSON" | jq 'length')" -eq 0 ]]; then
  echo "No failed jobs."
else
  echo "Failed/Non-success jobs"
  echo "$FAILED_JOBS_JSON" | jq -r '.[] | "- \(.name): \(.conclusion // .status) :: \(.html_url)"'
fi

echo
ANNOTATION_COUNT=0
PRINTED=0
LIMIT="$ANNOTATION_LIMIT"
echo "Annotations (up to $LIMIT)"

while IFS= read -r check_url; do
  [[ -z "$check_url" ]] && continue
  check_path="${check_url#https://api.github.com/}"
  annotations_json="$(gh api --paginate "$check_path/annotations?per_page=100" | jq -s 'add // []')"
  count="$(echo "$annotations_json" | jq 'length')"
  ANNOTATION_COUNT=$((ANNOTATION_COUNT + count))
  if [[ "$count" -gt 0 && "$PRINTED" -lt "$LIMIT" ]]; then
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$PRINTED" -ge "$LIMIT" ]]; then
        break
      fi
      echo "$line"
      PRINTED=$((PRINTED + 1))
    done < <(
      echo "$annotations_json" | jq -r '.[] | "- [\(.annotation_level)] \(.path):\(.start_line) \(.message)"'
    )
  fi
done < <(echo "$JOBS_JSON" | jq -r '.jobs[] | .check_run_url // empty')

if [[ "$ANNOTATION_COUNT" -eq 0 ]]; then
  echo "No annotations found."
else
  echo "Total annotations: $ANNOTATION_COUNT"
  if [[ "$ANNOTATION_COUNT" -gt "$PRINTED" ]]; then
    echo "(Showing first $PRINTED)"
  fi
fi
