#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Fetch CI run data locally (run/job/annotations/logs) and generate a triage summary.

Usage:
  scripts/gh_ci_pull_run.sh [--run <id> | --branch <name>] [--workflow <name>] [--event <event>] \
    [--repo <owner/repo>] [--out-dir <path>] [--required-only]

Examples:
  scripts/gh_ci_pull_run.sh --run 123456789
  scripts/gh_ci_pull_run.sh --branch epic/my-branch
  scripts/gh_ci_pull_run.sh --branch epic/my-branch --out-dir .tmp_untracked/ci/my-branch
USAGE
}

RUN_ID=""
BRANCH=""
WORKFLOW_NAME="PR CI"
EVENT_NAME="pull_request"
REPO=""
OUT_DIR=""
REQUIRED_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run)
      RUN_ID="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --workflow)
      WORKFLOW_NAME="$2"
      shift 2
      ;;
    --event)
      EVENT_NAME="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --required-only)
      REQUIRED_ONLY=1
      shift
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

if [[ -n "$RUN_ID" && -n "$BRANCH" ]]; then
  echo "Use either --run or --branch, not both." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required but not found in PATH." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found in PATH." >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "gh CLI is not authenticated. Run 'gh auth login' and retry." >&2
  exit 1
fi

if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

if [[ -z "$RUN_ID" ]]; then
  if [[ -z "$BRANCH" ]]; then
    BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  fi
  if [[ -z "$BRANCH" ]]; then
    echo "Unable to resolve branch. Pass --branch <name> or --run <id>." >&2
    exit 1
  fi

  run_list_tmp="$(mktemp)"
  run_list_err_tmp="$(mktemp)"
  if gh run list \
    --repo "$REPO" \
    --workflow "$WORKFLOW_NAME" \
    --branch "$BRANCH" \
    --event "$EVENT_NAME" \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId // ""' >"$run_list_tmp" 2>"$run_list_err_tmp"; then
    RUN_ID="$(cat "$run_list_tmp")"
  else
    run_list_error="$(tr '\n' ' ' < "$run_list_err_tmp")"
    rm -f "$run_list_tmp" "$run_list_err_tmp"
    echo "Failed to list runs for repo=$REPO branch=$BRANCH workflow=$WORKFLOW_NAME event=$EVENT_NAME." >&2
    echo "Details: $run_list_error" >&2
    exit 1
  fi
  rm -f "$run_list_tmp" "$run_list_err_tmp"
fi

if [[ -z "$RUN_ID" ]]; then
  echo "No run found for repo=$REPO branch=$BRANCH workflow=$WORKFLOW_NAME event=$EVENT_NAME." >&2
  exit 1
fi

if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR=".tmp_untracked/ci/runs/${RUN_ID}"
fi
mkdir -p "$OUT_DIR"

echo "Fetching run $RUN_ID from $REPO into $OUT_DIR"

gh run view "$RUN_ID" --repo "$REPO" \
  --json databaseId,name,workflowName,event,status,conclusion,url,headBranch,headSha,createdAt,updatedAt \
  > "$OUT_DIR/run.json"

gh api "repos/$REPO/actions/runs/$RUN_ID/jobs?per_page=100" > "$OUT_DIR/jobs.json"

gh run view "$RUN_ID" --repo "$REPO" --log-failed > "$OUT_DIR/failed.log" 2> "$OUT_DIR/failed.log.stderr" || true

annotations_tmp="$(mktemp)"
while IFS= read -r job_line; do
  check_url="$(printf '%s' "$job_line" | jq -r '.check_run_url // ""')"
  [[ -z "$check_url" ]] && continue
  check_path="${check_url#https://api.github.com/}"

  ann_json="$(gh api --paginate "$check_path/annotations?per_page=100" 2>/dev/null | jq -s 'add // []')"
  job_name="$(printf '%s' "$job_line" | jq -r '.name // "unknown-job"')"
  job_id="$(printf '%s' "$job_line" | jq -r '.id // 0')"

  printf '%s' "$ann_json" \
    | jq --arg job_name "$job_name" --argjson job_id "$job_id" \
      'map(. + {job_name: $job_name, job_id: $job_id})' \
    >> "$annotations_tmp"
  printf '\n' >> "$annotations_tmp"
done < <(jq -c '.jobs[]' "$OUT_DIR/jobs.json")

jq -s 'map(select(type == "array")) | add // []' "$annotations_tmp" > "$OUT_DIR/annotations.json"
rm -f "$annotations_tmp"

HEAD_BRANCH="$(jq -r '.headBranch // ""' "$OUT_DIR/run.json")"
PR_NUMBER=""
if [[ -n "$HEAD_BRANCH" ]]; then
  PR_NUMBER="$(gh pr list --repo "$REPO" --head "$HEAD_BRANCH" --state open --json number --jq '.[0].number // ""' 2>/dev/null || true)"
fi

if [[ -n "$PR_NUMBER" ]]; then
  if (( REQUIRED_ONLY == 1 )); then
    gh pr checks "$PR_NUMBER" --repo "$REPO" --required --json name,state,bucket,workflow,link \
      > "$OUT_DIR/pr_checks.json" 2> "$OUT_DIR/pr_checks.stderr" || true
  else
    gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,bucket,workflow,link \
      > "$OUT_DIR/pr_checks.json" 2> "$OUT_DIR/pr_checks.stderr" || true
  fi
  if [[ ! -s "$OUT_DIR/pr_checks.json" ]]; then
    printf '[]\n' > "$OUT_DIR/pr_checks.json"
  fi
else
  printf '[]\n' > "$OUT_DIR/pr_checks.json"
fi

total_jobs="$(jq '.jobs | length' "$OUT_DIR/jobs.json")"
failed_jobs="$(jq '[.jobs[] | select((.conclusion // "") != "success" and (.conclusion // "") != "skipped")] | length' "$OUT_DIR/jobs.json")"
annotations_total="$(jq 'length' "$OUT_DIR/annotations.json")"
annotations_errors="$(jq '[.[] | select((.annotation_level // "") == "failure")] | length' "$OUT_DIR/annotations.json")"
annotations_warnings="$(jq '[.[] | select((.annotation_level // "") == "warning")] | length' "$OUT_DIR/annotations.json")"

frontend_failed="$(jq '[.jobs[] | select((.conclusion // "") != "success" and (.name | test("Frontend Unit")))] | length' "$OUT_DIR/jobs.json")"
backend_failed="$(jq '[.jobs[] | select((.conclusion // "") != "success" and (.name | test("Backend")))] | length' "$OUT_DIR/jobs.json")"
e2e_failed="$(jq '[.jobs[] | select((.conclusion // "") != "success" and (.name | test("E2E")))] | length' "$OUT_DIR/jobs.json")"

{
  echo "# CI Triage Summary"
  echo
  echo "- Repository: \\`$REPO\\`"
  echo "- Run ID: \\`$RUN_ID\\`"
  echo "- Branch: \\`$HEAD_BRANCH\\`"
  if [[ -n "$PR_NUMBER" ]]; then
    echo "- PR: #$PR_NUMBER"
  else
    echo "- PR: none resolved from branch"
  fi
  echo "- Workflow: \\`$(jq -r '.workflowName // .name' "$OUT_DIR/run.json")\\`"
  echo "- Status: \\`$(jq -r '.status' "$OUT_DIR/run.json")\\`"
  echo "- Conclusion: \\`$(jq -r '.conclusion // "in_progress"' "$OUT_DIR/run.json")\\`"
  echo "- URL: $(jq -r '.url' "$OUT_DIR/run.json")"
  echo
  echo "## Jobs"
  jq -r '.jobs[] | "- [\(.conclusion // .status)] \(.name)"' "$OUT_DIR/jobs.json"
  echo
  echo "## Annotation Summary"
  echo "- Total: $annotations_total"
  echo "- Failures: $annotations_errors"
  echo "- Warnings: $annotations_warnings"
  echo
  echo "### Top Files"
  jq -r '
    group_by(.path // "(unknown)")
    | map({path: (.[0].path // "(unknown)"), count: length})
    | sort_by(-.count)
    | .[:10]
    | .[]
    | "- \(.path): \(.count)"
  ' "$OUT_DIR/annotations.json"
  echo
  echo "### Top Messages"
  jq -r '
    group_by((.message // "(no-message)") + "|" + (.path // "(unknown)"))
    | map({message: (.[0].message // "(no-message)"), path: (.[0].path // "(unknown)"), count: length})
    | sort_by(-.count)
    | .[:10]
    | .[]
    | "- \(.path): \(.message) (x\(.count))"
  ' "$OUT_DIR/annotations.json"
  echo
  echo "## Suggested Next Commands"
  if [[ "$backend_failed" -gt 0 ]]; then
    echo "- Backend failures detected: \\`uv run pytest -ra\\` and \\`uv run ruff check .\\`."
  fi
  if [[ "$frontend_failed" -gt 0 ]]; then
    echo "- Frontend unit failures detected: \\`cd ui && pnpm lint && pnpm typecheck && pnpm test\\`."
  fi
  if [[ "$e2e_failed" -gt 0 ]]; then
    echo "- E2E failures detected: \\`cd ui && pnpm test:e2e\\`."
  fi
  if [[ "$failed_jobs" -eq 0 ]]; then
    echo "- No failing jobs detected in this run."
  fi
  echo
  echo "## Local Artifacts"
  echo "- Run metadata: \\`$OUT_DIR/run.json\\`"
  echo "- Jobs: \\`$OUT_DIR/jobs.json\\`"
  echo "- PR checks: \\`$OUT_DIR/pr_checks.json\\`"
  echo "- Annotations: \\`$OUT_DIR/annotations.json\\`"
  echo "- Failed logs: \\`$OUT_DIR/failed.log\\`"
} > "$OUT_DIR/summary.md"

echo "Run pull complete."
echo "- jobs: $total_jobs"
echo "- failed_jobs: $failed_jobs"
echo "- annotations: $annotations_total"
echo "Summary: $OUT_DIR/summary.md"
